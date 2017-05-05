import os
import telepot
from subprocess import CalledProcessError, check_output, STDOUT
import tempfile
import logging
import logging.handlers
from telepot.delegate import per_chat_id, create_open, pave_event_space
import transmissionrpc
import math
import json
from datetime import datetime
from variables import Variables


rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.INFO)


def human_readable_timedelta(timedelta, precision=2):
    units = ('year', 'day', 'hour', 'minute', 'second', 'microsecond')

    delta = abs(timedelta)
    delta_dict =  {
        'year': int(delta.days / 365),
        'day': int(delta.days % 365),
        'hour': int(delta.seconds / 3600),
        'minute': int(delta.seconds / 60) % 60,
        'second': delta.seconds % 60,
    }

    hlist = []
    count = 0

    for unit in units:
        if count >= precision: break # met precision
        unit_value = delta_dict[unit]
        if unit_value== 0: continue # skip 0's
        s = '' if unit_value == 1 else 's' # handle plurals
        hlist.append('{} {}{}'.format(delta_dict[unit], unit, s))
        count += 1

    return format(', '.join(hlist)) + " ago"


def human_readable_file_size(size):
    if size == 0:
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return '%s %s' % (s, size_name[i])


class Flexget:
    def _run_flexget_command(self, flexget_command):
        return_code, result = run_shell_command("flexget " + flexget_command)
        if result and result.startswith("There is a FlexGet process already running"):
            result = '\n'.join(result.splitlines()[1:])
        return return_code, result

    def list(self):
        return_code, result = self._run_flexget_command("status --porcelain")
        if return_code!=0:
            return result

        statuses = self._parse_flexget_status(result)
        format_tasks = [self._status_to_markdown(s) for s in statuses]
        return format_tasks

    def _parse_flexget_status(self, status_result):
        lines = status_result.splitlines()
        headers = lines[0].split("|")
        headers = [item.strip() for item in headers]
        status_lines = lines[1:]
        tasks_data = []
        for line in status_lines:
            task_data = {}
            for index, field_data in enumerate(line.split("|")):
                task_data[headers[index]] = field_data.strip()
            tasks_data.append(task_data)
        return tasks_data

    def _status_to_markdown(self, status_data):
        task_name = status_data["Task"]
        last_exec = status_data["Last execution"]
        last_success = status_data["Last success"]

        if last_exec != "-":
            last_exec_date = datetime.strptime(last_exec, "%Y-%m-%d %H:%M")
            last_exec_desc = human_readable_timedelta(datetime.now() - last_exec_date)
        else:
            last_exec_desc = "Never"

        if last_success != "-":
            last_success_date = datetime.strptime(last_success, "%Y-%m-%d %H:%M")
            last_success_desc = human_readable_timedelta(datetime.now() - last_success_date)
        else:
            last_success_desc = "Never"

        return "*{task_name}*\nLast run: {last_exec_desc}\nLast success: {last_success_desc}".format(**locals())

    def execute(self, task_name):
        return task_name


class Transmission:
    def connect(self):
        return transmissionrpc.Client()

    def _torrent_to_markdown(self, torrent):
        return '\[{id}] *{name}*\n{status} | Size: {size} | {progress}%\nD/L:{dl_rate} | ETA:{eta}'\
            .format(id=torrent.id, name=torrent.name, status=torrent.status,
                    size=human_readable_file_size(torrent.totalSize), progress=round(torrent.progress, 2),
                    eta=torrent.format_eta(), dl_rate=(human_readable_file_size(torrent.rateDownload))+"/s")

    def list(self):
        try:
            c = self.connect()
            torrents = c.get_torrents()
        except transmissionrpc.TransmissionError:
            logging.error("Failed to connect to transmission")
            return ["Failed to connect to transmission"]

        if not torrents:
            return ["No torrents here"]

        format_torrents = [self._torrent_to_markdown(t) for t in torrents]
        return format_torrents

    def add(self, url):
        try:
            c = self.connect()
            new_torrent = c.add_torrent(url)
            return "Added new torrent : \[{id}] *{name}*".format(id=new_torrent.id, name=new_torrent.name)
        except transmissionrpc.TransmissionError:
            logging.error("Failed to connect to transmission")
            return "Failed to connect to transmission"

    def start(self, torrent_id):
        try:
            c = self.connect()
            c.start_torrent([torrent_id])
            return "Ok"
        except transmissionrpc.TransmissionError:
            logging.error("Failed to connect to transmission")
            return "Failed to connect to transmission"

    def stop(self, torrent_id):
        try:
            c = self.connect()
            c.stop_torrent([torrent_id])
            return "Ok"
        except transmissionrpc.TransmissionError:
            logging.error("Failed to connect to transmission")
            return "Failed to connect to transmission"

    def clean(self):
        try:
            c = self.connect()
            torrents = c.get_torrents()
            remove_ids = []
            for torrent in torrents:
                if torrent.leftUntilDone == 0:
                    remove_ids.append(torrent.id)

            if not remove_ids:
                return "No torrents to remove"
            else:
                c.remove_torrent(remove_ids)
                return "Removed {number} torrents".format(number=len(remove_ids))
        except transmissionrpc.TransmissionError:
            logging.error("Failed to connect to transmission")
            return "Failed to connect to transmission"


def join_path_to_script_directory(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)


def configure_log():
    root = logging.getLogger()
    log_file_name = join_path_to_script_directory("logs/bot.log")
    h = logging.handlers.RotatingFileHandler(log_file_name, maxBytes=1024*1024, backupCount=5)
    f = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')
    h.setFormatter(f)
    root.addHandler(h)


def text_to_tempfile(text):
    fd, path = tempfile.mkstemp()
    with open(path, 'w') as f:
        f.write(text)
    os.close(fd)
    return path


def run_shell_command(command):
    try:
        output = check_output(command, stderr=STDOUT, shell=True)
        return_code = 0
    except CalledProcessError as e:
        output = e.output
        return_code = e.returncode
    return return_code, str(output, 'utf-8')


def run_shell_command_and_reply_answer(command, sender):
    return_code, output = run_shell_command(command)
    if len(output) > 4096:
        temp_file_path = text_to_tempfile(output)
        sender.sendDocument(open(temp_file_path, 'rb'))
        os.remove(temp_file_path)
    else:
        sender.sendMessage(output)


def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None


class CommandHandler:
    def __init__(self, bot, text):
        self.bot = bot
        self.send_command_help_message()
        self.command_handler = self
        self.text = text

    def handle_command(self, text):
        pass

    def send_command_help_message(self):
        pass


class FlexgetListCommandHandler:
    def __init__(self, bot, text):
        for message in Flexget().list():
            bot.sender.sendMessage(message, parse_mode='Markdown')

        self.text = text
        bot.close()


class FlexgetExecuteCommandHandler(CommandHandler):
    def __init__(self, bot, text):
        super(FlexgetExecuteCommandHandler, self).__init__(bot, text)

    def handle_command(self, text):
        if not text:
            self.send_command_help_message()
            return
        self.bot.sender.sendMessage(Transmission.execute(text))
        self.bot.close()

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Please provide a task name or /cancel")


class FlexgetCommandHandler:
    def __init__(self, bot, text):
        self.bot = bot
        self.send_command_help_message()
        self.text = text
        self.command_handler = None

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Flexget help - /list /execute")

    def handle_command(self, text):
        if self.command_handler:
            self.command_handler.handle_command(text)
            return

        if len(text) == 0:
            self.send_command_help_message()
            return

        split_text = text.split()
        command = split_text[0][1:].lower()
        command_args = " ".join(split_text[1:])
        logging.info("received flexget command " + command)

        if command == "list":
            self.command_handler = FlexgetListCommandHandler(self.bot, command_args)
        elif command == "execute":
            self.command_handler = FlexgetExecuteCommandHandler(self.bot, command_args)
        else:
            self.send_command_help_message()


class TorrentAddCommandHandler(CommandHandler):
    def __init__(self, bot, text):
        super(TorrentAddCommandHandler, self).__init__(bot, text)

    def handle_command(self, text):
        if text is None or len(text) == 0:
            self.send_command_help_message()
            return
        self.bot.sender.sendMessage(Transmission().add(text), parse_mode='Markdown')
        self.bot.close()

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Please provide a magnet link or /cancel")


class TorrentListCommandHandler:
    def __init__(self, bot, text):
        for message in Transmission().list():
            bot.sender.sendMessage(message, parse_mode='Markdown')

        self.text = text
        bot.close()


class TorrentStartCommandHandler(CommandHandler):
    def __init__(self, bot, text):
        super(TorrentStartCommandHandler, self).__init__(bot, text)

    def handle_command(self, text):
        torrent_id = to_int(text)
        if torrent_id is None:
            self.send_command_help_message()
            return
        self.bot.sender.sendMessage(Transmission().start(torrent_id))
        self.bot.close()

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Please provide a torrent ID or /cancel")


class TorrentStopCommandHandler(CommandHandler):
    def __init__(self, bot, text):
        super(TorrentStopCommandHandler, self).__init__(bot, text)

    def handle_command(self, text):
        torrent_id = to_int(text)
        if torrent_id is None:
            self.send_command_help_message()
            return
        self.bot.sender.sendMessage(Transmission().stop(torrent_id))
        self.bot.close()

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Please provide a torrent ID or /cancel")


class TorrentCleanCommandHandler:
    def __init__(self, bot, text):
        bot.sender.sendMessage(Transmission().clean(), parse_mode='Markdown')

        self.text = text
        bot.close()

class TorrentCommandHandler:
    def __init__(self, bot, text):
        self.bot = bot
        self.send_command_help_message()
        self.text = text
        self.command_handler = None

    def send_command_help_message(self):
        self.bot.sender.sendMessage("Torrent help - /list /add /start /stop /clean")

    def handle_command(self, text):
        if self.command_handler:
            self.command_handler.handle_command(text)
            return

        if len(text) == 0:
            self.send_command_help_message()
            return

        split_text = text.split()
        command = split_text[0][1:].lower()
        command_args = " ".join(split_text[1:])
        logging.info("received torrent command " + command)

        if command == "add":
            self.command_handler = TorrentAddCommandHandler(self.bot, command_args)
        elif command == "list":
            self.command_handler = TorrentListCommandHandler(self.bot, command_args)
        elif command == "start":
            self.command_handler = TorrentStartCommandHandler(self.bot, command_args)
        elif command == "stop":
            self.command_handler = TorrentStopCommandHandler(self.bot, command_args)
        elif command == "clean":
            self.command_handler = TorrentCleanCommandHandler(self.bot, command_args)
        else:
            self.send_command_help_message()


class HomeBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(HomeBot, self).__init__(*args, **kwargs)
        self.command_handler = self

    def _on_torrent_command(self, text):
        self.command_handler = TorrentCommandHandler(self, text)

    def _on_flexget_command(self, text):
        self.command_handler = FlexgetCommandHandler(self, text)

    def _on_unknown_command(self, text):
        self.sender.sendMessage("Unknown command: " + text)
        self.close()

    def handle_command(self, text):
        split_text = text.split()
        command = split_text[0][1:].lower()
        command_args = " ".join(split_text[1:])
        if command == "torrents":
            self._on_torrent_command(command_args)
        elif command == "flexget":
            self._on_flexget_command(command_args)
        else:
            self._on_unknown_command(text)

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        user = msg["from"].get("username")
        if user != "barakwei":
            logging.error("User: {username} First: {first} Last: {last} ID: {id} is not authorized!".format(
                          username=msg["from"].get("username", ""), first=msg["from"].get("first_name", ""),
                          last=msg["from"].get("last_name", ""), id=msg["from"].get("id", "")))
            self.sender.sendMessage("Not authorized!")
            self.close()
            return
        else:
            logging.info("User is authorized")

        if content_type != "text":
            # log it
            return

        message = msg['text'].strip()
        logging.info("Message arrived: " + message)
        if message == "/cancel":
            self.close()

        self.command_handler.handle_command(message)

    def on__idle(self, event):
        self.sender.sendMessage('bye')
        self.close()


def main():
    configure_log()

    bot_token = Variables()["telegram_token"]

    bot = telepot.DelegatorBot(bot_token, [
        pave_event_space()(
            per_chat_id(), create_open, HomeBot, timeout=15),
    ])

    bot.message_loop(run_forever='Listening ...')


if __name__ == '__main__':
    main()

