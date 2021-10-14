#ifndef __lib_base_sigc_h__
#define __lib_base_sigc_h__

#include <sigc++/sigc++.h>

#define CONNECT(_signal, _slot) _signal.connect(sigc::mem_fun(*this, &_slot))

typedef sigc::connection	Connection;
typedef sigc::trackable		Object;

#define Signal0			sigc::signal0
#define Signal1			sigc::signal1
#define Signal2			sigc::signal2
#define Signal3			sigc::signal3
#define Signal4			sigc::signal4
#define Signal5			sigc::signal5

#define Slot0			sigc::slot0
#define Slot1			sigc::slot1
#define Slot2			sigc::slot2
#define Slot3			sigc::slot3
#define Slot4			sigc::slot4
#define Slot5			sigc::slot5

#define slot(x, y)		sigc::mem_fun(x, y)

#endif /* __lib_base_sigc_h__ */
