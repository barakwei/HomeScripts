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


rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.INFO)


def human_readable_file_size(size):
    if size == 0:
        return '0B'
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return '%s %s' % (s, size_name[i])


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
    return return_code, output


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
        self.sender.sendMessage(text)
        self.sender.sendChatAction('upload_document')
        temp_file_path = text_to_tempfile(text)
        self.sender.sendDocument(open(temp_file_path, 'rb'))
        os.remove(temp_file_path)

    def _on_unknown_command(self, text):
        self.sender.sendMessage("Unknown command: " + text)

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
        logging.error("Message arrived: " + message)
        if message == "/cancel":
            self.close()

        self.command_handler.handle_command(message)

    def on__idle(self, event):
        self.sender.sendMessage('bye')
        self.close()


def main():
    configure_log()

    config_file_path = join_path_to_script_directory('bot.json')

    with open(config_file_path) as config_file:
        config = json.load(config_file)

    bot_token = config["telegram_bot_token"]
    authorized_user = config["telegram_authorized_user"]

    bot = telepot.DelegatorBot(bot_token, [
        pave_event_space()(
            per_chat_id(), create_open, HomeBot, timeout=15),
    ])

    bot.message_loop(run_forever='Listening ...')


if __name__ == '__main__':
    main()

