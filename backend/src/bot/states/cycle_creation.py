from aiogram.fsm.state import State, StatesGroup


class CycleCreationFSM(StatesGroup):
    """
    FSM for the new feedback cycle creation process.
    """
    waiting_for_target_employee = State()
    waiting_for_respondents = State()
    waiting_for_deadline = State()
    confirming_creation = State()
