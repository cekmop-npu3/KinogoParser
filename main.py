from aiohttp import ClientSession
from asyncio import run, TaskGroup, sleep, Semaphore
from aiofiles import open as aio_open

from bs4 import BeautifulSoup as Bs
from re import search, DOTALL, finditer
from json import loads

from os import mkdir, listdir, PathLike
from shutil import rmtree
from os.path import exists
from subprocess import run as sub_run

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


class Kinogo:
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    cookies = {
        '__ddg3': 'bUiOBuOEfO5BEPty'
    }

    async def loadCookies(self, main_url: str) -> Cookies:
        async with ClientSession() as session:
            async with session.get(
                url=main_url,
                headers=self.headers,
                cookies=self.cookies
            ) as response:
                return dict(response.cookies)

    async def iframeUrl(self, page_url: str) -> str:
        async with ClientSession() as session:
            async with session.get(
                url=page_url,
                headers=self.headers,
                cookies=self.cookies
            ) as response:
                return Bs(await response.text(), 'lxml').find('ul', class_='js-player-tabs player-tabs').find('li').get('data-src')

    async def streamParams(self, iframe_url: str) -> StreamParams:
        async with ClientSession() as session:
            async with session.get(
                url=iframe_url,
                headers=self.headers
            ) as response:
                regex = r'let\s+playerConfigs\s+=\s+(.+?)var\s+player'
                return {
                    'url': f"https://{(iframeData := dict(loads(search(regex, (await response.text()).strip(), flags=DOTALL).groups()[0].strip()[:-1:]))).get('href')}/playlist/{iframeData.get('file').replace('~', '')}.txt",
                    'csrfToken': iframeData.get('key'),
                    'iframeUrl': iframe_url,
                    'streamHref': iframeData.get('href')
                }

    async def redirectUrl(self, stream_params: StreamParams) -> str:
        async with ClientSession() as session:
            async with session.post(
                    url=stream_params.get('url'),
                    headers=self.headers | {
                        'origin': stream_params.get('streamHref'),
                        'referer': stream_params.get('iframeUrl'),
                        'X-Csrf-Token': stream_params.get('csrfToken')
                    }
            ) as response:
                return await response.text()

    async def videoParams(self, redirect_url: str) -> VideoParams:
        async with ClientSession() as session:
            async with session.get(
                    url=redirect_url,
                    headers=self.headers
            ) as response:
                return {
                    'url': redirect_url.replace('/index.m3u8', ''),
                    'params': {int(obj.groups()[1]): obj.groups()[0] for obj in finditer(r'\.(/(\d+)/index\.m3u8)', await response.text())}
                }

    async def videoSegments(self, video_params: VideoParams) -> iter:
        async with ClientSession() as session:
            async with session.get(
                    url=f"{video_params.get('url')}{(params := video_params.get('params')).get(max(params.keys()))}",
                    headers=self.headers
            ) as response:
                return (obj.groups()[0] for obj in finditer(r'(https:.+?)\n#EXT', await response.text(), flags=DOTALL))

    async def loadFromSegment(self, semaphore: Semaphore, path_: str | PathLike, segment_url: str) -> None:
        async with semaphore:
            async with ClientSession() as session:
                async with session.get(
                    url=segment_url,
                    headers=self.headers
                ) as response:
                    regex = r"segment\d+\.ts"
                    await sleep(1)
                    async with aio_open(f'{path_}/{search(regex, segment_url).group()}', 'wb') as file:
                        await file.write(await response.read())

    @staticmethod
    def makeDir(path_: str | PathLike) -> None:
        if not exists('Films'):
            mkdir('Films')
        if not exists(path_):
            mkdir(path_)

    @staticmethod
    def makeTXT(path_: str | PathLike) -> str | PathLike:
        with open(f'{path_}/Segments.txt', 'w') as file:
            for file_name in sorted(filter(lambda x: x.endswith('.ts'), listdir(path_)), key=lambda x: int(search(r'\d+', x).group())):
                file.write(str(f"file '{file_name}'\n"))
        return f'{path_}/Segments.txt'

    async def downloadMP4(self, url: str) -> None:
        self.cookies.update(**(await self.loadCookies(url.split(regex := search(r'(\d+)', url).group())[0])))
        self.cookies['viewed_ids'] = regex
        self.makeDir(path_ := f'Films/{self.cookies.get("viewed_ids")}')
        semaphore = Semaphore(30)
        async with TaskGroup() as tg:
            [tg.create_task(self.loadFromSegment(semaphore, path_, seg)) for seg in await self.videoSegments(await self.videoParams(await self.redirectUrl(await self.streamParams(await self.iframeUrl(url)))))]
        sub_run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', self.makeTXT(path_), '-c', 'copy', f'Films/{regex}.mp4'])
        rmtree(path_, ignore_errors=True)


if __name__ == '__main__':
    run(Kinogo().downloadMP4('https://kinogo.biz/14939-zvezdnye-vojny-jepizod-1-skrytaja-ugroza.html'))
