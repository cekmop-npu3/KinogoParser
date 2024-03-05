from typing import TypedDict, Optional


class StreamParams(TypedDict):
    url: str
    csrfToken: Optional[str]
    iframeUrl: str
    streamHref: Optional[str]


class VideoParams(TypedDict):
    url: str
    params: dict[int, str]


class Cookies(TypedDict):
    __ddg1: str
    PHPSESSID: str


class ApiUtils:
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome'
                      '/121.0.0.0 Safari/537.36 OPR/107.0.0.0',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    cookies = {
        '__ddg3': 'krBwcsEVwDS3Op5Z'
    }


class Singleton(type):
    classes_ = {}

    def __call__(cls, *args, **kwargs) -> object:
        if cls not in cls.classes_.keys():
            cls.classes_[cls] = super().__call__(*args, **kwargs)
        return cls.classes_.get(cls)


class CookieException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
