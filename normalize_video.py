#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
#import locale
#import codecs
import re
import subprocess
import xml.dom.minidom
import logging

logging.basicConfig(filename="C:\Users\Salvador\Documents\AC3 Converter\log_normalize_video.txt", filemode="a", level=logging.INFO, format="[ %(asctime)s ] %(levelname)s : %(message)s")

# If the binaries of mediainfo and ffmpeg are not in the default path, 
# or if for any reason you want to specify an alternative location,
# you can do that by modifying the 'bin_*' variables.
# Examples:
# bin_mediainfo = "C:\\Users\\Gabriel\\Documents\\AC3 Converter\\mediainfo\\MediaInfo.exe"
# bin_ffmpeg = "/usr/local/bin/ffmpeg-v0.9"\
bin_mediainfo="\"C:\\Users\Salvador\\Documents\\AC3 Converter\\mediainfo\\MediaInfo.exe\""
bin_ffmpeg="\"C:\\Users\\Salvador\\Documents\\AC3 Converter\\ffmpeg\\bin\\ffmpeg.exe\""
bin_mkvmerge="\"C:\\Users\\Salvador\\Documents\\AC3 Converter\\mkvtoolnix\\mkvmerge.exe\""
bin_file="\"C:\\Users\\Salvador\\Documents\\AC3 Converter\\file\\bin\\file.exe\""

def get_video_files_list(folder_files):
    """Search for video files in a folder.

    Look into 'folder_files' directory and recursively searchs for files that have
    common video file extensions (mkv, mp4, avi, m2ts, m4v).
    """
    all_video_files = []
    for root, dirs, files in os.walk(folder_files):
        video_files = [os.path.join(root, file) for file in files if file.lower().endswith((".mkv", ".mp4", ".avi", ".m2ts", ".m4v"))]
        all_video_files.extend(video_files)
    return all_video_files


# MKV

def convert_format_mkv(filename_in, filename_out):
    
    logging.info("Converting MKV: {}".format(filename_in))

    # Extra flag to handle AVI files
    extra_flags = " "
    if extension.lower() == ".avi":
        extra_flags += "-fflags +genpts "

    # Convert to MKV
    command_str = "{} {} -y -i \"{}\" -c copy \"{}\"".format(bin_ffmpeg, extra_flags, filename_in, filename_out)
    exit_code = subprocess.call(command_str, shell=True)
    if exit_code == 0:
        logging.info("(OK) Converted MKV: {}".format(filename_in))
        return True
    else:
        logging.error("({}) converting MKV: {}".format(exit_code, filename_in))  
        return False

# AC3

def get_file_audio_format(filename):
    """Retrieve the audio format of a video file.

    Inspects 'filename' and returns the format (codec) of the first audio track.
    """
    try:
        xml_data = subprocess.check_output([bin_mediainfo.replace("\"", ""), "--Output=XML", filename])
        media = xml.dom.minidom.parseString(xml_data)
        audio_tracks = [[info.firstChild.nodeValue for info in track.childNodes if info.nodeName == "Format"][0] for track in media.getElementsByTagName("track") if track.attributes['type'].value == "Audio"]
    except:
        audio_tracks = ["???"]
    return audio_tracks

def convert_audio_ac3(filename_in, filename_out):

    logging.info("Converting AC-3: {}".format(filename_in))
    
    command_str = "{} -y -i \"{}\" -i \"{}\" -c copy -c:a:0 ac3 -ab 640k -map 0 -map 1:a:0 \"{}\"".format(bin_ffmpeg, filename_in, filename_in, filename_out)
    exit_code = subprocess.call(command_str, shell=True)
    if exit_code == 0:
        logging.info("(OK) Converted AC-3: {}".format(filename_original))
        return True
    else:
        logging.error("({}) converting AC-3: {}".format(exit_code, filename_original))
        return False


# Subtitle

def get_file_tracks(filename):
    mkv_metadata = subprocess.check_output([bin_mkvmerge.replace("\"", ""), "--identify", filename])
    mkv_tracks = re.findall("ID da faixa (\d+): (\S+) \(([^\)]+)\)", mkv_metadata) 
    if len(mkv_tracks) == 0:
        mkv_tracks = re.findall("Track ID (\d+): (\S+) \(([^\)]+)\)", mkv_metadata) 
    return mkv_tracks

def search_normalize_subtitle(filename_original):

    filedir = os.path.dirname(filename_original)
    filename, extension = os.path.splitext(filename_original)
    filename_subtitle = filename+".srt"

    if os.path.exists(filename_subtitle):
        logging.info("Found subtitle \"{}\" for \"{}\"".format(filename_subtitle, filename_original))
        try:
            subtitle_fileoutput = subprocess.check_output([bin_file.replace("\"", ""), "-bi", filename_subtitle]).decode("utf-8")
            subtitle_encoding = re.search("charset=(\S+)", subtitle_fileoutput).group(1)
            if subtitle_encoding == "unknown-8bit":
                subtitle_encoding = "Windows-1252"
            subtitle_rawcontent = open(filename_subtitle).read()
            subtitle_content = subtitle_rawcontent.decode(subtitle_encoding)

            filename_subtitle_converted = "{}/subtitle.srt".format(filedir)
            with open(filename_subtitle_converted, "w") as outfile:
                outfile.write(subtitle_content.encode("utf-8"))
            logging.info("Converted subtitle \"{}\" into \"{} ({} to UTF-8)\"".format(filename_subtitle, filename_subtitle_converted, subtitle_encoding))

            if not os.path.exists("{}/Subs".format(filedir)):
                os.mkdir("{}/Subs".format(filedir))
            filename_subtitle_backup = "{}/Subs/{}".format(filedir, os.path.basename(filename_subtitle))
            os.rename(filename_subtitle, filename_subtitle_backup)
            logging.info("Backuped subtitle \"{}\" into \"{}\"".format(filename_subtitle, filename_subtitle_backup))

            return filename_subtitle_converted

        except Exception, error:
            logging.error("Converting subtitle \"{}\": {}".format(filename_subtitle, error))
            return None
            
    else:
        logging.info("No subtitle found for \"{}\"".format(filename_original))
        return None

def attach_subtitle(filename_original, filename_in, filename_out, subtitle_language="por"):

    # Search for external subtitle
    filename_external_subtitle = search_normalize_subtitle(filename_original)
    if filename_external_subtitle:
        subtitle_params = "--sub-charset 0:UTF-8 --default-track 0:true --language 0:{} \"{}\"".format(subtitle_language, filename_external_subtitle)
    else:
        subtitle_params = ""

    # Get list of tracks
    tracks_all      = get_file_tracks(filename_in)
    tracks_video    = [tid for (tid, ttype, tformat) in tracks_all if ttype == "video"]
    tracks_audio    = [tid for (tid, ttype, tformat) in tracks_all if ttype == "audio"]
    tracks_subtitle = [tid for (tid, ttype, tformat) in tracks_all if ttype == "subtitles"]
    tracks_other    = [tid for (tid, ttype, tformat) in tracks_all if ttype not in ("video", "audio", "subtitles")]

    # Set default tracks
    flags_video = ["--default-track {}:{}".format(track, "true" if i == 0 else "false") for (i, track) in enumerate(tracks_video)]
    flags_audio = ["--default-track {}:{}".format(track, "true" if i == 0 else "false") for (i, track) in enumerate(tracks_audio)]
    if filename_external_subtitle:
        flags_subtitle = ["--default-track {}:false".format(track) for (i, track) in enumerate(tracks_subtitle)]
    else:
        flags_subtitle = ["--default-track {}:{}".format(track, "true" if i == 0 else "false") for (i, track) in enumerate(tracks_subtitle)]
    flags_other = ["--default-track {}:{}".format(track, "true" if i == 0 else "false") for (i, track) in enumerate(tracks_other)]
    flags_all = " ".join(flags_video + flags_audio + flags_subtitle + flags_other)

    # Set order of the tracks
    order_video = ["0:{}".format(track) for track in tracks_video]
    order_audio = ["0:{}".format(track) for track in tracks_audio]
    if filename_external_subtitle:
        order_subtitle = ["1:0"]+["0:{}".format(track) for track in tracks_subtitle]
    else:
        order_subtitle = ["0:{}".format(track) for track in tracks_subtitle]
    order_other = ["0:{}".format(track) for track in tracks_other]
    order_all = ",".join(order_video + order_audio + order_subtitle + order_other)

    # Attach subtitle and normalize tracks
    logging.info("Normalizing tracks and attaching subtitle: {}".format(filename_in))
    command_str = "{} --disable-track-statistics-tags -o \"{}\" {} \"{}\" {} --track-order {}".format(bin_mkvmerge, filename_out, flags_all, filename_in, subtitle_params, order_all)
    exit_code = subprocess.call(command_str, shell=True)
    if filename_external_subtitle:
        os.remove(filename_external_subtitle)
    if exit_code == 0:
        logging.info("(OK) Normalized and attached: {}".format(filename_original))
        return True
    else:
        logging.error("({}) normalizing and attaching: {}".format(exit_code, filename_original))
        return False


# Main

if __name__ == "__main__":
          
    import argparse
    arguments = argparse.ArgumentParser(description="Normalize video files by (1) converting it to MKV, (2) creating an AC-3 audio track, (3) attaching an external subtitle and (4) ordering and setting as default the tracks of the MKV")
    arguments.add_argument("local_name", help="File or folder to convert.")
    arguments.add_argument("--mode", required=False, default="backup", choices=["new", "backup", "replace"], help="File management mode: 'new' the converted file will have a suffix and it will keep the original file intact; 'backup' the converted file will replace the original, but a backup of the original file will be made a suffix; 'replace' the converted file will replace the original file.")
    params = arguments.parse_args()
    
    print "Looking for video files"
    if os.path.isdir(params.local_name):
        video_files = get_video_files_list(params.local_name)
    else:
        video_files = [params.local_name]

    print "Videos found: {} items".format(len(video_files))
    for i, filename_original in enumerate(video_files):
        print "+ ({}/{}) processing \"{}\"".format(i+1, len(video_files), filename_original)

        filedir = os.path.dirname(filename_original)
        filename, extension = os.path.splitext(filename_original)
        filename_in = filename+extension
        filename_out = filename+"-NEW.mkv"
        filename_temp = "{}/temp.mkv".format(filedir)

        if not os.path.exists("{}.log".format(filename)):
            fh = logging.FileHandler(filename="{}.log".format(filename), mode="w")
            fh.setLevel(logging.INFO)
            fh.setFormatter(logging.Formatter("[ %(asctime)s ] %(levelname)s : %(message)s"))
            logging.getLogger("").addHandler(fh)

            logging.info("Started processing \"{}\"".format(filename_original))

            status_ok = True 

            # Convert audio track to AC-3
            audio_formats = get_file_audio_format(filename_in)
            if "AC-3" not in audio_formats and "MPEG Audio" not in audio_formats:
            #if False:
                status = convert_audio_ac3(filename_in, filename_temp)
                if not status:
                    status_ok = False
                filename_in = filename+".mkv"
                filename_temp2 = filename_temp

            # Convert video file to MKV format
            elif not filename_original.lower().endswith(".mkv"):
                status = convert_format_mkv(filename_in, filename_temp)
                if not status:
                    status_ok = False
                filename_in = filename+".mkv"
                filename_temp2 = filename_temp

            # No AC-3 or MKV conversion necessary
            else:
                filename_temp2 = filename_in

            # Attach subtitles and normalize tracks
            if status_ok:
                status = attach_subtitle(filename_original, filename_temp2, filename_out)
                if not status:
                    status_ok = False

            # Verify execution and rename
            if status_ok:
                if params.mode != "new":
                    filename_old = filename+"-BACKUP"+extension
                    os.rename(filename_original, filename_old);
                    os.rename(filename_out, filename_in);
                    if params.mode == "replace":
                        os.remove(filename_old)
                logging.info("Renamed files in mode \"{}\"".format(params.mode)) 
            else:
                if os.path.exists(filename_out):
                    os.remove(filename_out)
                logging.error("Failed processing \"{}\"".format(filename_original)) 

            # Remove temporary file
            if os.path.exists(filename_temp):
                os.remove(filename_temp)

            logging.info("Finished processing \"{}\"".format(filename_original))
            
            logging.getLogger("").removeHandler(fh)

