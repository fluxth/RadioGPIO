from enum import Enum, IntFlag

class ModuleStatus(IntFlag):
    Disabled = 0
    Enabled = 1
    Initialized = 2
    Running = 3
    Warning = 4
    Error = 5
    ReservedStatus1 = 6
    ReservedStatus2 = 7

    Activity = 8
    KeepActivity = 16

class ModuleStatusMask(IntFlag):
    StatusMask = 7
    ActivityMask = 8
    KeepActivityMask = 16

class ActionSequenceItemType(Enum):
    NoOp = 0
    Wait = 1
    RunOutputCommand = 2

class ModuleIOType(Enum):
    Invalid = 0
    Input = 1
    Output = 2
    Bidirectional = 3