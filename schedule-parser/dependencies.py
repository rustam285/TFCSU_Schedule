from functools import lru_cache

from app.service.implementation.he_parser_service import HEParserService
from app.service.implementation.logger_service import LoggerService
from app.service.implementation.parser_service import ParserService
from app.service.implementation.part_time_parser_service import PTParserService
from app.service.implementation.sve_parser_service import SVEParserService


@lru_cache(maxsize=1)
def get_logger_service() -> LoggerService:
    return LoggerService()


@lru_cache(maxsize=1)
def get_parser_service() -> ParserService:
    return ParserService(get_he_parser_service(), get_sve_parser_service(), get_pt_parser_service())


@lru_cache(maxsize=1)
def get_he_parser_service() -> HEParserService:
    return HEParserService()


@lru_cache(maxsize=1)
def get_sve_parser_service() -> SVEParserService:
    return SVEParserService()


@lru_cache(maxsize=1)
def get_pt_parser_service() -> PTParserService:
    return PTParserService()
