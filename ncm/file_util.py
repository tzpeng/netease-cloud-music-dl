# -*- coding: utf-8 -*-

from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, APIC, TPE1, TIT2, TALB, TRCK, USLT, SYLT, error
from PIL import Image
import re


def resize_img(file_path, max_size=(640, 640), quality=90):
    try:
        img = Image.open(file_path)
    except IOError:
        print('Can\'t open image:', file_path)
        return

    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
        img.thumbnail(max_size, Image.ANTIALIAS)
        img = img.convert('RGB')
        img.save(file_path, quality=quality)


def add_metadata_to_song(file_path, cover_path, lyric_path, song, is_program=False):
    # If no ID3 tags in mp3 file
    try:
        audio = MP3(file_path, ID3=ID3)
    except HeaderNotFoundError:
        print('Can\'t sync to MPEG frame, not an validate MP3 file!')
        return

    if audio.tags is None:
        print('No ID3 tag, trying to add one!')
        try:
            audio.add_tags()
            audio.save()
        except error as e:
            print('Error occur when add tags:', str(e))
            return

    # Modify ID3 tags
    id3 = ID3(file_path)
    # Remove old 'APIC' frame
    # Because two 'APIC' may exist together with the different description
    # For more information visit: http://mutagen.readthedocs.io/en/latest/user/id3.html
    if id3.getall('APIC'):
        id3.delall('APIC')
    # add album cover
    id3.add(
        APIC(
            encoding=0,         # 3 is for UTF8, but here we use 0 (LATIN1) for 163, orz~~~
            mime='image/jpeg',  # image/jpeg or image/png
            type=3,             # 3 is for the cover(front) image
            data=open(cover_path, 'rb').read()
        )
    )
    # add artist name
    if is_program:
        art_name = song['dj']['nickname']
    else:
        art_name = song['artists'][0]['name']
    id3.add(
        TPE1(
            encoding=3,
            text=art_name
        )
    )
    # add Unsychronised lyric
    lyric = open(lyric_path, 'rb').read().decode('utf-8')
    unsync_lyric = []
    for line in lyric.split("\n"):
        if line.find("]") != -1:
            lyric_str = line.split("]")[1]
            unsync_lyric.append(lyric_str + '\n')
    # print(unsync_lyric)
    id3.add(
        USLT(
            encoding=3,
            lang='chs',
            desc="Unsychronised lyric",
            text=''.join(unsync_lyric)
        )
    )
    # https://cloud.tencent.com/developer/ask/sof/924227
    # add Synchronized lyric
    sync_lyric = []
    for line in lyric.split("\n"):
        # print(line)
        if line.find("]") != -1:
            time_str = line.split("]")[0].replace("[","")
            lyric_str = line.split("]")[1]
            try:
                time_array = re.findall(r"\d+:\d+\.\d+", time_str)
                if len(time_array) == 1:
                    time_m = int(time_array[0].split(":")[0])
                    time_s = int(time_array[0].split(":")[1].split(".")[0])
                    time_ms = int(time_array[0].split(":")[1].split(".")[1])
                    sync_lyric.append((lyric_str, time_m*60*1000+time_s*1000+time_ms))
            except:
                print(time_str)
    # print(sync_lyric)
    id3.add(
        SYLT(
            encoding=3,
            lang='chs',
            format=2,
            type=1,
            desc="Synchronized lyric",
            text=sync_lyric
        )
    )
    # add song name
    id3.add(
        TIT2(
            encoding=3,
            text=song['name']
        )
    )
    # add album name
    if is_program:
        album_name = song['dj']['brand']
    else:
        album_name = song['album']['name']
    id3.add(
        TALB(
            encoding=3,
            text=album_name
        )
    )
    # add track no
    if not is_program:
        id3.add(
            TRCK(
                encoding=3,
                text="%s/%s" % (song['no'], song['album']['size'])
            )
        )
    # programs doesn't have a valid album info.
    id3.save(v2_version=3)
