#!/usr/bin/python3
"""Monitors bluetooth devices and turns on/off the light automatically.

Requires: `apt-get install bluez libbluetooth-dev`
"""

import datetime
import sys
import time
from typing import IO

import bt_proximity
import requests
import yaml
from absl import app, logging


class TuyaBt:
  def __init__(self, fp: IO[str]) -> None:
    config = yaml.safe_load(fp)
    self.rssi_objects = [
        bt_proximity.BluetoothRSSI(x) for x in config['devices']
    ]
    self.begin, self.end = (datetime.time(x) for x in config['hours'])
    self.auth = config['gateway']['auth']
    self.url = config['gateway']['url']

  def request(self, what: str) -> None:
    payload = {'what': what, 'auth': self.auth}
    exception: Exception
    for _ in range(5):
      try:
        status = requests.post(self.url, json=payload).json()['status']
        logging.info('Request status: %s', status)
        return
      except KeyError as e:
        exception = e
        continue
      except requests.RequestException as e:
        exception = e
        continue
    else:
      raise exception

  @property
  def is_in_active_hours(self) -> bool:
    return self.begin <= datetime.datetime.now().time() <= self.end

  @property
  def active_device_count(self) -> int:
    count = 0
    for rssi_object in self.rssi_objects:
      rssi = rssi_object.request_rssi()
      if rssi is not None:
        rssi = rssi[0]
      logging.debug('RSSI of %s: %s', rssi_object.addr, rssi)
      if rssi is not None and rssi > -30:
        count += 1
    return count

  @staticmethod
  def main(argv):
    if len(argv) < 2:
      logging.error('Usage: %s config.yml', argv[0])
      sys.exit(1)

    with open(argv[1], 'r') as fp:
      tuyabt = TuyaBt(fp)

    curr_state = 'on'
    curr_lost = 0

    while True:
      if tuyabt.active_device_count > 0:
        curr_lost = 0
        if curr_state == 'off':
          if tuyabt.is_in_active_hours:
            curr_state = 'on'
            logging.info('Device found, turn on the light')
            tuyabt.request('turn_on')
          else:
            logging.debug('Device found, but keep the light off')
      else:  # device not found
        if curr_state != 'off':
          if curr_lost >= 3:
            curr_lost = 0
            curr_state = 'off'
            logging.info('Device not found, turn off the light')
            tuyabt.request('turn_off')
          else:
            curr_lost += 1
            logging.debug('Current lost count: %d', curr_lost)
      time.sleep(1)


if __name__ == '__main__':
  app.run(TuyaBt.main)
