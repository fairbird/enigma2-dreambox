#ifndef __lib_base_sigc_h__
#define __lib_base_sigc_h__

#include <sigc++/sigc++.h>

#define CONNECT(_signal, _slot) _signal.connect(sigc::mem_fun(*this, &_slot))

typedef sigc::connection	Connection;
typedef sigc::trackable		Object;

#define Signal0			sigc::signal
#define Signal1			sigc::signal
#define Signal2			sigc::signal
#define Signal3			sigc::signal
#define Signal4			sigc::signal
#define Signal5			sigc::signal

#define Slot0			sigc::slot
#define Slot1			sigc::slot
#define Slot2			sigc::slot
#define Slot3			sigc::slot
#define Slot4			sigc::slot
#define Slot5			sigc::slot

#define slot(x, y)		sigc::mem_fun(x, y)

#endif /* __lib_base_sigc_h__ */
