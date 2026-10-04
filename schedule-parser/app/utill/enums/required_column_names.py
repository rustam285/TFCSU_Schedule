from enum import Enum


class RequiredColumnNames(Enum):
    DN = 'д/н'
    NUMBER = '№'
    WEEK1 = '1 неделя'
    WEEK2 = '2 неделя'
    AUD = '№ ауд.'

class RequiredSVEColumnNames(Enum):
    DN = 'д/н'
    NUMBER = '№'
    WEEK1 = '1 неделя'
    WEEK2 = '2 неделя'
    AUD = 'ауд.'

class RequiredPartTimeColumnNames(Enum):
    DATE = 'Дата'
    NUMBER = '№ пары'
    AUD = '№ ауд.'
