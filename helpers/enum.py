from enum import Enum

class ModuleStatus(Enum):
    Disabled = 0
    Enabled = 1
    Initialized = 2
    Running = 3
    Warning = 4
    Error = 5

    ActivityRunning = 10
    ActivityWarning = 11
    ActivityKeepWarning = 12
    ActivityError = 13
    ActivityKeepError = 14

class ActionSequenceItemType(Enum):
    NoOp = 0
    Wait = 1
    RunOutputCommand = 2