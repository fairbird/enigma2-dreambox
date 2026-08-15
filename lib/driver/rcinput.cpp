#include <lib/driver/rcinput.h>

#include <lib/base/eerror.h>

#include <sys/ioctl.h>
#include <linux/input.h>
#include <linux/kd.h>
#include <sys/stat.h>
#include <fcntl.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

int eRCDeviceInputDev::getGamepadButtonKey(unsigned int code) const
{
	/* Standard Linux gamepad button layout. */
	switch (code)
	{
		case BTN_SOUTH: return KEY_OK;
		case BTN_EAST: return KEY_EXIT;
		case BTN_WEST: return KEY_MENU;
		case BTN_NORTH: return KEY_INFO;
		case BTN_TL: return KEY_CHANNELDOWN;
		case BTN_TR: return KEY_CHANNELUP;
		case BTN_TL2: return KEY_VOLUMEDOWN;
		case BTN_TR2: return KEY_VOLUMEUP;
		case BTN_SELECT: return KEY_EPG;
		case BTN_START: return KEY_MENU;
		case BTN_MODE: return KEY_HOMEPAGE;
		case BTN_DPAD_UP: return KEY_UP;
		case BTN_DPAD_DOWN: return KEY_DOWN;
		case BTN_DPAD_LEFT: return KEY_LEFT;
		case BTN_DPAD_RIGHT: return KEY_RIGHT;
	}

	/*
	 * Legacy USB encoders expose numbered joystick buttons instead of the
	 * standardized BTN_SOUTH layout.  This order matches the common
	 * 081f:e401 SNES-style controller and equivalent generic encoders.
	 */
	switch (code)
	{
		case BTN_TRIGGER: return KEY_MENU;       // X / button 0
		case BTN_THUMB: return KEY_OK;           // A / button 1
		case BTN_THUMB2: return KEY_EXIT;        // B / button 2
		case BTN_TOP: return KEY_INFO;           // Y / button 3
		case BTN_TOP2: return KEY_CHANNELDOWN;   // L / button 4
		case BTN_PINKIE: return KEY_CHANNELUP;   // R / button 5
		case BTN_BASE: return KEY_VOLUMEDOWN;    // L2 / button 6
		case BTN_BASE2: return KEY_VOLUMEUP;     // R2 / button 7
		case BTN_BASE3: return KEY_EPG;          // Select / button 8
		case BTN_BASE4: return KEY_MENU;         // Start / button 9
	}
	return KEY_RESERVED;
}

void eRCDeviceInputDev::handleGamepadAxis(const struct input_event &event)
{
	int negativeKey;
	int positiveKey;
	switch (event.code)
	{
		case ABS_X:
		case ABS_HAT0X:
			negativeKey = KEY_LEFT;
			positiveKey = KEY_RIGHT;
			break;
		case ABS_Y:
		case ABS_HAT0Y:
			negativeKey = KEY_UP;
			positiveKey = KEY_DOWN;
			break;
		default:
			return;
	}

	struct input_absinfo info = {};
	if (!static_cast<eRCInputEventDriver *>(driver)->getAbsInfo(event.code, info) || info.maximum <= info.minimum)
		return;
	const int center = info.minimum + ((info.maximum - info.minimum) / 2);
	int deadzone = (info.maximum - info.minimum) / 4;
	if (deadzone < 1)
		deadzone = 1;

	int state = 0;
	if (event.value <= center - deadzone)
		state = -1;
	else if (event.value >= center + deadzone)
		state = 1;

	const int oldState = gamepadAxisStates[event.code];
	if (state == oldState)
		return;
	if (oldState)
		input->keyPressed(eRCKey(this, oldState < 0 ? negativeKey : positiveKey, eRCKey::flagBreak));
	if (state)
		input->keyPressed(eRCKey(this, state < 0 ? negativeKey : positiveKey, eRCKey::flagMake));
	gamepadAxisStates[event.code] = state;
}

void eRCDeviceInputDev::handleCode(long rccode)
{
	struct input_event *ev = (struct input_event *)rccode;

	if (isgamepad && ev->type == EV_ABS)
	{
		handleGamepadAxis(*ev);
		return;
	}

	if (ev->type != EV_KEY)
		return;

	if (isgamepad)
	{
		const int mappedCode = getGamepadButtonKey(ev->code);
		if (mappedCode == KEY_RESERVED)
			return;
		ev->code = mappedCode;
	}

	int km = iskeyboard ? input->getKeyboardMode() : eRCInput::kmNone;

	switch (ev->code)
	{
		case KEY_LEFTSHIFT:
		case KEY_RIGHTSHIFT:
			shiftState = ev->value;
			break;
		case KEY_CAPSLOCK:
			if (ev->value == 1)
				capsState = !capsState;
			break;
	}

	if (km == eRCInput::kmAll)
		return;

	if (km == eRCInput::kmAscii)
	{
		bool ignore = false;
		bool ascii = ev->code > 0 && ev->code < 59;

		switch (ev->code)
		{
			case KEY_LEFTCTRL:
			case KEY_RIGHTCTRL:
			case KEY_LEFTSHIFT:
			case KEY_RIGHTSHIFT:
			case KEY_LEFTALT:
			case KEY_RIGHTALT:
			case KEY_CAPSLOCK:
				ignore = true;
				break;
			case KEY_RESERVED:
			case KEY_ESC:
			case KEY_TAB:
			case KEY_BACKSPACE:
			case KEY_ENTER:
			case KEY_INSERT:
			case KEY_DELETE:
			case KEY_MUTE:
				ascii = false;
			default:
				break;
		}

		if (ignore)
			return;

		if (ascii)
		{
			if (ev->value)
			{
				if (consoleFd >= 0)
				{
					struct kbentry ke;
					/* off course caps is not the same as shift, but this will have to do for now */
					ke.kb_table = (shiftState || capsState) ? K_SHIFTTAB : K_NORMTAB;
					ke.kb_index = ev->code;
					::ioctl(consoleFd, KDGKBENT, &ke);
					if (ke.kb_value)
						input->keyPressed(eRCKey(this, ke.kb_value & 0xff, eRCKey::flagAscii)); /* emit */
				}
			}
			return;
		}
	}

#if KEY_PLAY_ACTUALLY_IS_KEY_PLAYPAUSE
	if (ev->code == KEY_PLAY)
	{
		if (id == "dreambox advanced remote control (native)")
		{
			/* 8k rc has a KEY_PLAYPAUSE key, which sends KEY_PLAY events. Correct this, so we do not have to place hacks in the keymaps. */
			ev->code = KEY_PLAYPAUSE;
		}
	}
#endif

	switch (ev->value)
	{
		case 0:
			input->keyPressed(eRCKey(this, ev->code, eRCKey::flagBreak)); /*emit*/
			break;
		case 1:
			input->keyPressed(eRCKey(this, ev->code, 0)); /*emit*/
			break;
		case 2:
			input->keyPressed(eRCKey(this, ev->code, eRCKey::flagRepeat)); /*emit*/
			break;
	}
}

eRCDeviceInputDev::eRCDeviceInputDev(eRCInputEventDriver *driver, int consolefd)
	:	eRCDevice(driver->getDeviceName(), driver), iskeyboard(driver->isKeyboard()),
		isgamepad(driver->isGamepad()),
		ismouse(driver->isPointerDevice()),
		consoleFd(consolefd), shiftState(false), capsState(false)
{
	setExclusive(true);
	eDebug("[eRCDeviceInputDev] device \"%s\" is a %s", id.c_str(), iskeyboard ? "keyboard" : (isgamepad ? "gamepad" : (ismouse ? "mouse" : "remotecontrol")));
}

void eRCDeviceInputDev::setExclusive(bool b)
{
	if (!iskeyboard && !ismouse)
		driver->setExclusive(b);
}

const char *eRCDeviceInputDev::getDescription() const
{
	return id.c_str();
}

class eInputDeviceInit
{
	struct element
	{
		public:
			char* filename;
			eRCInputEventDriver* driver;
			eRCDeviceInputDev* device;
			element(const char* fn, eRCInputEventDriver* drv, eRCDeviceInputDev* dev):
				filename(strdup(fn)),
				driver(drv),
				device(dev)
			{
			}
			~element()
			{
				delete device;
				delete driver;
				free(filename);
			}
		private:
			element(const element& other); /* no copy */
	};
	typedef std::vector<element*> itemlist;
	std::vector<element*> items;
	int consoleFd;

public:
	eInputDeviceInit()
	{
		int i = 0;
		consoleFd = ::open("/dev/tty0", O_RDWR);
		while (1)
		{
			char filename[32];
			sprintf(filename, "/dev/input/event%d", i);
			if (::access(filename, R_OK) < 0)
				break;
			add(filename);
			++i;
		}
		eDebug("[eInputDeviceInit] Found %d input devices.", i);
	}

	~eInputDeviceInit()
	{
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
			delete *it;

		if (consoleFd >= 0)
			::close(consoleFd);
	}

	void add(const char* filename)
	{
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
		{
			if (strcmp((*it)->filename, filename) == 0)
			{
				// Ignore if already exists
				return;
			}
		}
		eDebug("[eInputDeviceInit] adding device %s", filename);
		eRCInputEventDriver *p = new eRCInputEventDriver(filename);
		items.push_back(new element(filename, p, new eRCDeviceInputDev(p, consoleFd)));
	}

	void remove(const char* filename)
	{
		for (itemlist::iterator it = items.begin(); it != items.end(); ++it)
		{
			if (strcmp((*it)->filename, filename) == 0)
			{
				delete *it;
				items.erase(it);
				return;
			}
		}
		eDebug("[eInputDeviceInit] Remove '%s', not found", filename);
	}
};

eAutoInitP0<eInputDeviceInit> init_rcinputdev(eAutoInitNumbers::rc+1, "input device driver");

void addInputDevice(const char* filename)
{
	init_rcinputdev->add(filename);
}

void removeInputDevice(const char* filename)
{
	init_rcinputdev->remove(filename);
}
