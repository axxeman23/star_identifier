import json
import sys
import os
import pathlib
import log
import glob
import urllib.request
import threading
from queue import Queue
from identifier_stash_interface import IdentifierStashInterface

current_path = str(pathlib.Path(__file__).parent.absolute())
performer_export_folder = str(pathlib.Path(current_path + '/../star-identifier-performers/').absolute())

IMAGE_TYPES = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp'
}

def main():
  json_input = readJSONInput()

  output = {}

  run(json_input)

  out = json.dumps(output)
  print(out + "\n")


def readJSONInput():
  json_input = sys.stdin.read()
  return json.loads(json_input)

def _debugPrint(input):
  f = open(os.path.join(current_path, 'debug.txt'), 'w')
  f.write(str(input))
  f.close()

def run(json_input):
  log.LogInfo('==> running')
  mode_arg = json_input['args']['mode']
  client = IdentifierStashInterface(json_input["server_connection"])

  if mode_arg == "" or mode_arg == "identify":
    identify(client)
  elif mode_arg == "export_known":
    exportKnown(client)

def identify(client):
  client

def exportKnown(client, nmb_threads=8):
  log.LogInfo('Getting all performer images...')
  
  performers = client.getPerformerImages()
  total = len(performers)

  log.LogInfo(f"Found {total} performers")

  if total == 0:
    log.LogError('No performers found.')
    return

  os.makedirs(performer_export_folder, exist_ok=True)

  performer = performers[0]

  # res = urllib.request.urlopen(performer['image_path'])
  # info = res.info()
  # log.LogInfo(f"==> image info type: {info.get_content_type()}")
  # ext = IMAGE_TYPES[res.info().get_content_type()]
  # log.LogInfo(f"==> image ext: {ext}")
  # path = os.path.join(performer_export_folder, f"{performer['name']}-{performer['id']}.{ext}")
  # log.LogInfo(f"==> image ext: {path}")
  
  # with open(path, "wb") as f:
  #   f.write(res.read())
  

  # nmb of finished performers
  count = 0
  # in the rare case that there are fewer threads than performers
  nmb_threads = min(nmb_threads, total)
  thread_lock = threading.Lock()
  q = Queue(maxsize=0)

  for performer in performers:
      q.put(performer)

  os.makedirs(performer_export_folder, exist_ok=True)

  log.LogInfo('Starting performer image export (this might take a while)')
  
  # Create threads and start them
  for i in range(nmb_threads):
      worker = threading.Thread(target=export_thread_function, name=f"Thread-{i}", args=(q, thread_lock, count, total, client))
      worker.start()

  # Wait for all threads to be finished
  q.join()
  log.LogInfo(f'Finished exporting all {total} performer images')
  # _debugPrint(performers)

def export_thread_function(q: Queue, thread_lock: threading.Lock, count: int, total: int, client: IdentifierStashInterface):
  log.LogDebug(f"Created {threading.current_thread().name}")
  while not q.empty():
    performer = q.get()

    filename = f"{performer['name']}%{performer['id']}"

    # Check if the image exists, ignoring the extension
    if not glob.glob(os.path.join(performer_export_folder, f"{filename}.*")):
      res = urllib.request.urlopen(performer['image_path'])
      ext = IMAGE_TYPES[res.info().get_content_type()]
      path = os.path.join(performer_export_folder, f"{performer['name']}%{performer['id']}.{ext}")

      with open(path, 'wb') as f:
        f.write(res.read())
    
    thread_lock.acquire()
    count += 1
    log.LogProgress(count / total)
    thread_lock.release()

    q.task_done()

  log.LogDebug(f"{threading.current_thread().name} finished")
  return True

      

def get_scrape_tag(client):
    tag_name = "star identifier"
    tag_id = client.findTagIdWithName(tag_name)
    if tag_id is not None:
        return tag_id
    else:
        client.createTagWithName(tag_name)
        tag_id = client.findTagIdWithName(tag_name)
        return tag_id

def findImages(client):
  log.LogInfo('Getting all images...')
  images = client.findImages()
  total = len(images)
  log.LogInfo(f"Found {total} images")

  tag_id = get_scrape_tag(client)
  image_filter = {
			"tags": {
				"value": [tag_id],
				"modifier": "INCLUDES_ALL"
			}
		}
  images = client.findImages(image_filter)
  log.LogInfo(f"Found {len(images)} tagged images")

  _debugPrint(images[0])


main()


# https://github.com/ageitgey/face_recognition
# https://github.com/ageitgey/face_recognition/issues/175