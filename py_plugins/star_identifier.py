import json
import sys
import log
from stash_interface import StashInterface


def main():
  json_input = readJSONInput()

  client = StashInterface(json_input.get('server_connection'))
  sayHello()

  output = {
    'output': 'ok'
  }

  print(json.dumps(output) + '\n') 


def readJSONInput():
  json_input = sys.stdin.read()
  return json.loads(json_input)


def sayHello():
  log.LogInfo('Hello World!')


main()
