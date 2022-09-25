# -*- coding: utf-8 -*-

import os
import re
import requests

from ncm import config
from ncm.api import CloudApi
from ncm.file_util import add_metadata_to_song
from ncm.file_util import resize_img


def get_song_info_by_id(song_id):
    api = CloudApi()
    song = api.get_song(song_id)
    return song


def download_song_by_id(song_id, download_folder, sub_folder=True):
    # get song info
    song = get_song_info_by_id(song_id)
    download_song_by_song(song, download_folder, sub_folder)


def download_song_by_song(song, download_folder, sub_folder=True, program=False):
    # get song info
    api = CloudApi()
    song_id = song['id']
    song_name = format_string(song['name'])
    if program:
        artist_name = format_string(song['dj']['nickname'])
        album_name = format_string(song['dj']['brand'])
    else:
        artist_name = format_string(song['artists'][0]['name'])
        album_name = format_string(song['album']['name'])

    # update song file name by config
    song_file_name = '{}.mp3'.format(song_name)
    switcher_song = {
        1: song_file_name,
        2: '{} - {}.mp3'.format(artist_name, song_name),
        3: '{} - {}.mp3'.format(song_name, artist_name)
    }
    song_file_name = switcher_song.get(config.SONG_NAME_TYPE, song_file_name)

    # update song folder name by config, if support sub folder
    if sub_folder:
        switcher_folder = {
            1: download_folder,
            2: os.path.join(download_folder, artist_name),
            3: os.path.join(download_folder, artist_name, album_name),
        }
        song_download_folder = switcher_folder.get(config.SONG_FOLDER_TYPE, download_folder)
    else:
        song_download_folder = download_folder

    # download song
    if program:
        song_url = api.get_program_url(song, level="standard")
    else:
        song_url = api.get_song_url(song_id)

    if song_url is None:
        print('Song <<{}>> is not available due to copyright issue!'.format(song_name))
        return
    is_already_download = download_file(song_url, song_file_name, song_download_folder)
    if is_already_download:
        print('Mp3 file already download:', song_file_name)
        return

    # download cover
    if program:
        cover_url = song['coverUrl']
    else:
        cover_url = song['album']['blurPicUrl']

    if cover_url is None:
        if program:
            cover_url = song['mainSong']['album']['picUrl']
        else:
            cover_url = song['album']['picUrl']
    cover_file_name = 'cover_{}.jpg'.format(song_id)
    download_file(cover_url, cover_file_name, song_download_folder)

    # download lyric
    lyric = api.get_lyric(song_id)
    lyric_file_name = 'lyric_{}.lrc'.format(song_id)
    write_file(lyric.encode('utf-8'), lyric_file_name, song_download_folder)

    # resize cover
    resize_img(os.path.join(song_download_folder, cover_file_name))

    # add metadata for song
    song_file_path = os.path.join(song_download_folder, song_file_name)
    cover_file_path = os.path.join(song_download_folder, cover_file_name)
    lyric_file_path = os.path.join(song_download_folder, lyric_file_name)
    add_metadata_to_song(song_file_path, cover_file_path, lyric_file_path, song, program)

    # delete cover file
    os.remove(cover_file_path)

    # delete lyric file
    os.remove(lyric_file_path)


def write_file(lyric, file_name, folder):
    print('Save lyric: ' + file_name)
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, file_name)
    lrc_file = open(file_path, 'wb')
    lrc_file.write(lyric)
    lrc_file.close()
    return False


def download_file(file_url, file_name, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)
    file_path = os.path.join(folder, file_name)

    response = requests.get(file_url, stream=True)
    length = int(response.headers.get('Content-Length'))

    # TODO need to improve whether the file exists
    if os.path.exists(file_path) and os.path.getsize(file_path) > length:
        return True

    progress = ProgressBar(file_name, length)

    with open(file_path, 'wb') as file:
        for buffer in response.iter_content(chunk_size=1024):
            if buffer:
                file.write(buffer)
                progress.refresh(len(buffer))
    return False


class ProgressBar(object):

    def __init__(self, file_name, total):
        super().__init__()
        self.file_name = file_name
        self.count = 0
        self.prev_count = 0
        self.total = total
        self.end_str = '\r'

    def __get_info(self):
        return 'Progress: {:6.2f}%, {:8.2f}KB, [{:.30}]' \
            .format(self.count / self.total * 100, self.total / 1024, self.file_name)

    def refresh(self, count):
        self.count += count
        # Update progress if down size > 10k
        if (self.count - self.prev_count) > 10240:
            self.prev_count = self.count
            print(self.__get_info(), end=self.end_str)
        # Finish downloading
        if self.count >= self.total:
            self.end_str = '\n'
            print(self.__get_info(), end=self.end_str)


def format_string(string):
    """
    Replace illegal character with ' '
    """
    return re.sub(r'[\\/:*?"<>|\t]', ' ', string)
