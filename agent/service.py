from __future__ import annotations

import os
import sys

try:
    import servicemanager
    import win32event
    import win32service
    import win32serviceutil
except ImportError:  # pragma: no cover
    servicemanager = None
    win32event = None
    win32service = None
    win32serviceutil = object

from agent.agent import main as agent_main


class ClassroomAgentService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
    _svc_name_ = "ClassroomAgent"
    _svc_display_name_ = "Classroom Agent Service"

    def __init__(self, args: list[str]) -> None:
        super().__init__(args)
        self.h_wait_stop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self) -> None:  # noqa: N802
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.h_wait_stop)

    def SvcDoRun(self) -> None:  # noqa: N802
        servicemanager.LogInfoMsg("Classroom Agent Service starting")
        os.environ.setdefault("PYTHONUNBUFFERED", "1")
        agent_main()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ClassroomAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ClassroomAgentService)
