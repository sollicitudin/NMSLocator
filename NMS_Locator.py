import json
import os
import datetime
import time
import configparser
import ocr
import csv
import winsound
from copy import deepcopy
from screenshot_crop import crop_screenshot
from table_output import BHTable
from colorclass import Windows
from pyperclip import copy

def get_current_location(last_save):
    with open(last_save, "r", encoding='utf-8') as save_file:
        save_file_string = save_file.read()[:-1]
    parsed_save = json.loads(save_file_string)

    json_player_data = parsed_save['6f=']["yhJ"]["oZw"]

    Player_State = {'x':json_player_data["dZj"], 'y':json_player_data['IyE'], 'z':json_player_data["uXE"], 'ssi':json_player_data['vby']}
    galactic_address = format_galaxtic_coord(Player_State['x'], Player_State['y'], Player_State['z'], Player_State['ssi'])

    if not check_if_address_exists(galactic_address):
        time_logged = datetime.datetime.now()
        enter_address_into_log(galactic_address, time_logged)
        table_handler.output_address(galactic_address, config.getboolean('SETTINGS', 'STREAMER_MODE'))
        copy(galactic_address)

        return(galactic_address)
    else:
        return None


def get_file_mod_time(file):
    return os.path.getmtime(file)


def get_latest_save_file():
    all_save_files = []
    for(dirpath, dirnames, filenames) in os.walk(os.getenv('APPDATA') + os.sep + "HelloGames" + os.sep + "NMS"):
        for file in filenames:
            if file[-3:] == ".hg" and file[:3] != "mf_":
                all_save_files.append(os.path.join(dirpath, file))
    latest_save = max(all_save_files, key=os.path.getmtime)
    return latest_save


def get_latest_screenshot():
    all_screenshot_files = []
    exclude = set(["thumbnails"])
    for (dirpath, dirnames, filenames) in os.walk(config.get('SETTINGS', 'SCREENSHOT_DIRECTORY')):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for file in filenames:
            if file[-4:] == ".jpg" or file[-4:] == '.png':
                all_screenshot_files.append(os.path.join(dirpath, file))

    try:
        latest_save = max(all_screenshot_files, key=os.path.getmtime)
    except ValueError:
        print('No screenshot found in screenshot directory on latest check')
        latest_save = None

    # if latest file is already cropped it means we've already processed it, so skip it
    if latest_save:
        if os.path.isfile("cropped" + os.sep + os.path.splitext(os.path.basename(latest_save))[0] + "_cropped.png"):
            latest_save = None

    return latest_save


def check_if_address_exists(galactic_address):
    if any(galactic_address in entry for entry in location_log):
        return True


def is_date_in_log(date):
    for entry in location_log:
        if entry[0].date() == date.date():
            return True
    return False


def enter_address_into_log(galactic_address, dt):
    with open(log_loc, "a") as log:
        log.write(dt.strftime("%B %d %Y %I:%M:%S %p") + ',' + galactic_address + '\n')
    with open(log_dir + os.sep + "bulk.log", 'a') as bulk:
        if is_date_in_log(dt):
            bulk.write(galactic_address + '\n')
        else:
            bulk.write('\n' + dt.strftime("%B %d %Y") + '\n')
            bulk.write(galactic_address + '\n')

    location_log.append([dt, galactic_address])


def format_galaxtic_coord(x, y, z, ssi):
    fmt = "{0:0{1}X}"
    parts = [str(fmt.format(x + 2047, 4)), str(fmt.format(y + 127, 4)), str(fmt.format(z + 2047, 4)), str(fmt.format(ssi,4))]
    return(':'.join(parts))


def load_log():
    try:
        os.makedirs(log_dir)
    except FileExistsError:
        pass
    try:
        open(log_dir + os.sep + "location_log.log", 'r')
    except IOError:
        open(log_dir + os.sep + "location_log.log", 'w')

    location_log = []
    with open(log_dir + os.sep + "location_log.log") as log:
        line = log.readline().strip()
        while line:
            split_line = line.split(',')
            location_log.append([datetime.datetime.strptime(split_line[0], "%B %d %Y %I:%M:%S %p"), split_line[1]])
            line = log.readline().strip()

    return location_log, log_dir + os.sep + "location_log.log"


def create_bulk_log():
    if not os.path.isfile(log_dir + os.sep + "bulk.log"):
        try:
            open(log_dir + os.sep + "bulk.log", 'a')
        except IOError:
            open(log_dir + os.sep + "bulk.log", 'w')


def update_csv(completed_bh_pairing):
    csv_dir = log_dir

    if config.get('SETTINGS', 'CSV_DIRECTORY').upper() != 'DEFAULT':
        csv_dir = config.get('SETTINGS', 'CSV_DIRECTORY')

    try:
        open(csv_dir + os.sep + "black_holes.csv", 'r')
    except IOError:
        open(csv_dir + os.sep + "black_holes.csv", 'w')

    fieldnames = ['bh-address', 'bh-system', 'bh-region', 'bh-econ', 'bh-life',
                  'exit-address', 'exit-system', 'exit-region', 'exit-econ', 'exit-life']

    with open(csv_dir + os.sep + "black_holes.csv", 'a') as bhfile:
        writer = csv.DictWriter(bhfile, lineterminator='\n', fieldnames=fieldnames)
        if os.path.getsize(csv_dir + os.sep + "black_holes.csv") == 0:
            writer.writeheader()

        writer.writerow(completed_bh_pairing)

    bhfile.close()


def load_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    if config.get('SETTINGS', 'SCREENSHOT_DIRECTORY') == 'None' and config.getboolean('SETTINGS', 'OCR') is True:
        raise SystemExit("SCREENSHOT_DIRECTORY has not been set in your config.ini, this must be set to run")
    return config


def handle_bh_pairing_logic(completed_system_info, completed_bh_pairing):
    if completed_system_info['address'][-2:] == '79' and not completed_bh_pairing:
        # This is a black hole system!
        # print('Storing Black Hole system ' + completed_system_info['system'] + '...\n')
        if config.getboolean('SETTINGS', 'PLAY_NOTIFICATION') and os.path.isfile('sounds\\system_notification.wav'):
            winsound.PlaySound('sounds\\system_notification.wav', winsound.SND_FILENAME)
        for key in list(completed_system_info):
            completed_bh_pairing['bh-' + key] = completed_system_info.pop(key)
    elif completed_system_info['address'][-2:] != '79' and not completed_bh_pairing:
        print("Starting from a system that is not a black hole is not supported by this tool at this time.")
    elif completed_system_info['address'][-2:] == '79' and completed_bh_pairing:
        # This is if both the start and exit are black holes, this shouldn't really happen unless near the center
        # and if they are near the center it will be the same black hole
        raise SystemExit("Got two consecutive black hole addresses", completed_bh_pairing,
                         completed_system_info, "Cannot reconcile this. DOES NOT COMPUTE")
    elif completed_system_info['address'][-2:] != '79' and completed_bh_pairing:
        # This is the second half of a bh pairing
        # print('Storing Exit system ' + completed_system_info['system'] + '...\n')
        for key in list(completed_system_info):
            completed_bh_pairing['exit-' + key] = completed_system_info.pop(key)

    return completed_system_info, completed_bh_pairing


def gather_system_info():
    galactic_address = None
    system_info = {}
    completed_system_info = {}
    completed_bh_pairing = {}
    try:
        while True:
            last_modded_save = get_latest_save_file()
            last_modded_save_time = os.path.getmtime(last_modded_save)

            if last_modded_save_time >= int(round(time.time())) - 30 and not galactic_address:
                galactic_address = get_current_location(last_modded_save)
                if galactic_address and not system_info:
                    if config.getboolean('SETTINGS', 'PLAY_NOTIFICATION') and os.path.isfile('sounds\\data_notification.wav'):
                        winsound.PlaySound('sounds\\data_notification.wav', winsound.SND_FILENAME)

            if config.getboolean('SETTINGS', 'OCR'):
                last_screenshot = get_latest_screenshot()
                if last_screenshot:
                    cropped_screen = crop_screenshot(last_screenshot)
                    ocr_info = ocr.ocr_screenshot(cropped_screen, config.get('SETTINGS', 'TESSERACT_LOC'))
                    if ocr_info:
                        system_info = deepcopy(ocr_info)
                        table_handler.output_ocr_info(ocr_info)
                        ocr_info.clear()
                        if not galactic_address:
                            if config.getboolean('SETTINGS', 'PLAY_NOTIFICATION') and os.path.isfile('sounds\\data_notification.wav'):
                                winsound.PlaySound('sounds\\data_notification.wav', winsound.SND_FILENAME)

                if galactic_address and system_info:
                    completed_system_info = deepcopy(system_info)
                    completed_system_info.update({'address': galactic_address})
                    galactic_address = None
                    system_info.clear()

                    completed_system_info, completed_bh_pairing = handle_bh_pairing_logic(completed_system_info, completed_bh_pairing)
                    completed_system_info.clear()

                    if 'bh-address' in completed_bh_pairing.keys() and 'exit-address' in completed_bh_pairing.keys():
                        print('Completed BH pairing and logging to CSV!')
                        time_logged = datetime.datetime.now()
                        print(time_logged.strftime("Time logged: %B %d %I:%M:%S %p"))
                        print(completed_bh_pairing['bh-system'] + ' System -> ' + completed_bh_pairing['exit-system'] + ' System ')
                        update_csv(completed_bh_pairing)
                        if config.getboolean('SETTINGS', 'PLAY_NOTIFICATION') and os.path.isfile('sounds\\bh_logged_notification.wav'):
                            winsound.PlaySound('sounds\\bh_logged_notification.wav', winsound.SND_FILENAME)
                        table_handler.next_blackhole()
                        completed_bh_pairing.clear()

            time.sleep(15)
    except KeyboardInterrupt:
        pass


log_dir = os.getenv('LOCALAPPDATA') + os.sep + 'Programs' + os.sep + "NMS Locator"
config = load_config()
location_log, log_loc = load_log()
create_bulk_log()
save = get_latest_save_file()
mod_times = []
table_handler = BHTable()
Windows.enable(auto_colors=True, reset_atexit=True)
print("Waiting for new locations every 15 seconds.\nNew locations will be copied to clipboard and displayed...\n")
gather_system_info()
