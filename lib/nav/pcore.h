#ifndef __lib_nav_pcore_h
#define __lib_nav_pcore_h

#include <lib/nav/core.h>
#include <lib/python/connections.h>

class eNavigation;

/* a subset of eNavigation */
class pNavigation: public iObject, public sigc::trackable
{
    DECLARE_REF(pNavigation);
public:
	enum RecordType {
	    isRealRecording          =     1,
	    isStreaming              =     2,
	    isPseudoRecording        =     4,
	    isUnknownRecording       =     8,
	    isFromTimer              =  0x10,
	    isFromInstantRecording   =  0x20,
	    isFromEPGrefresh         =  0x40,
	    isFromSpecialJumpFastZap =  0x80,
	    isAnyRecording           =  0xFF
	};

    PSignal1<void, int> m_event;
    PSignal2<void, ePtr<iRecordableService>&, int> m_record_event;

    pNavigation(int decoder = 0);

    RESULT playService(const eServiceReference &service);
    RESULT stopService();
    RESULT pause(int p);
    SWIG_VOID(RESULT) getCurrentService(ePtr<iPlayableService> &SWIG_OUTPUT);

    SWIG_VOID(RESULT) recordService(const eServiceReference &ref, ePtr<iRecordableService> &SWIG_OUTPUT, bool simulate=false, RecordType type=isUnknownRecording);
    RESULT stopRecordService(ePtr<iRecordableService> &service);
    void getRecordings(std::vector<ePtr<iRecordableService> > &recordings, bool simulate=false, RecordType type=isAnyRecording);
    void getRecordingsServicesOnly(std::vector<eServiceReference> &services, pNavigation::RecordType type=isAnyRecording);
    void getRecordingsTypesOnly(std::vector<pNavigation::RecordType> &services, pNavigation::RecordType type=isAnyRecording);
    void getRecordingsSlotIDsOnly(std::vector<int> &slotids, pNavigation::RecordType type=isAnyRecording);
    std::map<ePtr<iRecordableService>, eServiceReference, std::less<iRecordableService*> > getRecordingsServices(RecordType type=isAnyRecording);
    void navEvent(int event);

private:
    ePtr<eNavigation> m_core;
    ePtr<eConnection> m_nav_event_connection, m_nav_record_event_connection;
    void navRecordEvent(ePtr<iRecordableService>, int event);
};

#endif
