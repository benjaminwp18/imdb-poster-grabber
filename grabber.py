from urllib.request import urlopen, Request
from PIL import Image
from io import BytesIO
import os
import re

CODES_FILE = 'imdb_codes.txt'
POSTERS_DIR = 'posters'
ROOT_URL = 'https://www.imdb.com/title/'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
POSTER_DIMENSIONS = (145, 400)  # Height is big to not affect resizing


class MovieMetadata:
    def __init__(self, imdb_code: str, url: str, media_url: str, title: str):
        self.imdb_code = imdb_code
        self.url = url
        self.media_url = media_url
        self.title = title


def get_page_html(url):
    page_request = Request(url, headers=HEADERS)
    html = urlopen(page_request).read().decode("utf-8")
    return html


def get_filepath(filename, extension='', number=None):
    full_filename = filename + ('' if number is None else f'.{number}') + \
        extension
    return os.path.join(POSTERS_DIR, full_filename)


def download_posters(metadatas):
    i = 0
    length = len(metadatas)
    for metadata in metadatas:
        i += 1
        media_url = metadata.media_url
        title = metadata.title

        print(f'({i} / {length}) Downloading posters for {title} at {media_url}')

        page_request = Request(media_url, headers=HEADERS)
        html = urlopen(page_request).read().decode("utf-8")

        imgs = re.findall('<img.*?/>', html)
        imgs = [re.sub(r'<img.*?src=[\'"](.*?)[\'"].*?/>', r'\g<1>', img) for img in
                imgs if ('.jpg' in img or '.png' in img or '//fls-' not in img)]

        counter = 1
        for media_url in imgs:
            print(f'\t\tDownloading image {media_url}')

            extension = re.sub(r'.*(\..*?)$', r'\g<1>', media_url)
            filepath = get_filepath(title, extension,
                                    counter if len(imgs) > 1 else None)

            img_request = Request(media_url, headers=HEADERS)
            pil_image = Image.open(BytesIO(urlopen(img_request).read()))
            pil_image.thumbnail(POSTER_DIMENSIONS)
            pil_image.save(filepath)

            counter += 1


def choose_keepers():
    posters = os.listdir(POSTERS_DIR)

    by_title = {}
    for poster in posters:
        if poster == '.gitkeep':
            # Ignore .gitkeep file that keeps the "posters" dir in the repo
            continue

        split = poster.split('.')

        if len(split) != 3:
            print(f'File {poster} has the wrong name format. Ignoring.')
            continue

        if split[0] not in by_title:
            by_title[split[0]] = {}

        by_title[split[0]][split[1]] = poster

    for movie in by_title.items():
        title: str = movie[0]
        files: dict[str, str] = movie[1]
        num_posters = len(files)

        keeper_number = None
        while True:
            keeper_number = input(f'{title} poster (1-{num_posters})? ')

            if keeper_number in files:
                break
            else:
                print(f'Please choose a number (1-{num_posters}).')

        for poster_number in files.keys():
            if poster_number != keeper_number:
                os.remove(get_filepath(files[poster_number]))

        old_name_split = files[keeper_number].split('.')
        new_name = old_name_split[0] + '.' + old_name_split[2]
        os.rename(get_filepath(files[keeper_number]), get_filepath(new_name))


def load_movie_metadata():
    metadatas = []

    print('Loading IMDB codes...')
    with open(CODES_FILE) as f:
        raw_lines = f.readlines()
        print('Codes loaded\n')

        codes = []

        for code in raw_lines:
            if code[0] == '#':  # Ignore comments
                continue
            if code[-1] == '\n':  # Remove newline
                code = code[:-1]

            codes.append(code)

        length = len(codes)

        for c, code in enumerate(codes):
            url = f'{ROOT_URL}{code}/'
            print(f'({c + 1} / {length}) Finding media for {url}')

            try:
                html = get_page_html(url)
            except Exception:
                print('Failed to get page. Your code might be invalid.')
                continue

            title = re.findall(r'<title>.*?</title>', html)[0]  # Isolate title element
            title = re.sub(r'<title/?>', '', title)             # Strip element tags
            title = re.sub(r'(.*?) \(.*', r'\g<1>', title)       # Remove " (1983) - IMDB"
            title = "".join(char for char in title if char.isalnum())  # Sanitize
            print(f'\tTitle: "{title}"')

            media_url = url + re.findall(r'mediaviewer/.*?"', html)[0][:-1]
            print(f'\tMedia found at {media_url}')

            metadatas.append(MovieMetadata(code, url, media_url, title))

    return metadatas

if __name__ == '__main__':
    print(' --- LOADING MOVIE METADATA --- ')
    metadatas = load_movie_metadata()

    print(' --- DOWNLOADING POSTERS --- ')
    download_posters(metadatas)

    choice = input('Done downloading. Choose posters to keep (in order if asc name)? (Y/n) ')
    if choice.lower() != 'n':
        choose_keepers()
