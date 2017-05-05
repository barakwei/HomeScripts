import requests
from pathlib import Path
import json
import arrow
import math
from pprint import pprint

class Crashplan(object):
    """
    Provides access to Crashplan consumer information.
    """
    BASE_API_URL = "https://account.crashplan.com/api/"

    class SubscriptionInfo(object):
        def __init__(self, subscription_dict):
            self.name = subscription_dict["name"]
            self.expirationDate = arrow.get(subscription_dict["expirationDate"])

    class ComputerInfo(object):
        def __init__(self, computer):
            self.name = computer["name"]
            self.last_connected = arrow.get(computer["lastConnected"])
            self.total_backup_size = computer["backupUsage"][0]["selectedBytes"]
            self.backup_todo = computer["backupUsage"][0]["todoBytes"]
            selectedBytes = int(computer["backupUsage"][0]["selectedBytes"])
            todoBytes = int(computer["backupUsage"][0]["todoBytes"])
            percentComplete = 1 - (todoBytes / selectedBytes)
            self.percentComplete = round(percentComplete * 100 ,2)
            self.last_completed = arrow.get(computer["backupUsage"][0]["lastCompletedBackup"])
            self.selected_files = computer["backupUsage"][0]["selectedFiles"]

    def __init__(self, username, password):
        self.auth = (username, password)

    def fetch_url_json(self, url):
        return json.loads(requests.get(url, auth=self.auth).text)

    def get_account_id(self):
        MY_ACCOUNT_URL = self.BASE_API_URL + "Account/my"
        data = self.fetch_url_json(MY_ACCOUNT_URL)
        return data["data"]["accountId"]

    def get_subscription(self):
        SUBSCRIPTION_URL = self.BASE_API_URL + "Subscription?accountId=" + str(self.get_account_id())
        data = self.fetch_url_json(SUBSCRIPTION_URL)
        subs = data["data"]
        if not subs:
            return None
        
        sorted_subs = sorted(subs, key=lambda s: arrow.get(s["expirationDate"]), reverse=True)
        if arrow.get(sorted_subs[0]["expirationDate"]) < arrow.now():
            return None

        return self.SubscriptionInfo(sorted_subs[0])
        
    def computers(self):
        COMPUTERS_URL = self.BASE_API_URL + "computer?active=true&incBackupUsage=true&srtKey=lastBackup"
        data = self.fetch_url_json(COMPUTERS_URL)
        computers = data["data"]["computers"]
        return list(map(lambda c: self.ComputerInfo(c), filter(lambda c: c["backupUsage"], computers)))
