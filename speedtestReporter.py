#!/usr/bin/python3

import logging
import logging.handlers
import speedtest
import thingspeak
import traceback
import json
import os

rootLogger = logging.getLogger('')
rootLogger.setLevel(logging.INFO)

def joinPathToScriptDirectory(path):
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), path)

def configure_log():
    root = logging.getLogger()
    log_file_name = joinPathToScriptDirectory('speedtest.log')    
    h = logging.handlers.RotatingFileHandler(log_file_name, maxBytes=1024*1024, backupCount=5)
    f = logging.Formatter('%(asctime)s %(name)s %(levelname)-8s %(message)s')
    h.setFormatter(f)
    root.addHandler(h)

def main():
    configure_log()

    global channel

    try:
        config_file_path = joinPathToScriptDirectory('thingspeak.json')
        
        with open(config_file_path) as config_file:
            config = json.load(config_file)

        channel_id = config["channel"]
        write_key = config["writekey"]

        #for server in speedtest.list_servers():
        #    print('%(id)4s) %(sponsor)s (%(name)s, %(country)s) ''[%(d)0.2f km]' % server)

        ping, download, upload, server = speedtest.test_speed(timeout=30, secure=True)
        download = download /(1000.0*1000.0)*8
        upload = upload /(1000.0*1000.0)*8

        logging.info('Ping %dms; Download: %2f; Upload %2f', ping, download, upload)
        channel = thingspeak.Channel(id=channel_id, write_key=write_key)
        response = channel.update({1: ping, 2: download, 3: upload})
        print(response)
    except KeyboardInterrupt:
        print('\nCancelling...')
        speedtest.cancel_test()
    except Exception:
        logging.exception("Exception has occurred")
        traceback.print_exc()


if __name__ == '__main__':
    main()
