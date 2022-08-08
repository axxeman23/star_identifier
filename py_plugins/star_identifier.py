import json
import sys
import os
import pathlib
import log
import urllib.request
import face_recognition
import numpy as np
from identifier_stash_interface import IdentifierStashInterface

current_path = str(pathlib.Path(__file__).parent.absolute())
encoding_export_folder = str(pathlib.Path(current_path + '/../star-identifier-encodings/').absolute())

encodings_path = os.path.join(encoding_export_folder, 'star-identifier-encodings.npz')
errors_path = os.path.join(encoding_export_folder, 'errors.json')

tag_name = "star identifier"

def main():
  json_input = readJSONInput()

  output = {}

  run(json_input)

  out = json.dumps(output)
  print(out + "\n")

def readJSONInput():
  json_input = sys.stdin.read()
  return json.loads(json_input)

def jsonPrint(input, path):
  os.makedirs(encoding_export_folder, exist_ok=True)
  f = open(path, 'w')
  json.dump(input, f)
  f.close()

def jsonRead(path):
  f = open(path, 'w')
  data = json.load(f)
  f.close()
  return data

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

#
# export function
#

def exportKnown(client):
  log.LogInfo('Getting all performer images...')
  
  performers = client.getPerformerImages()
  total = len(performers)

  log.LogInfo(f"Found {total} performers")

  if total == 0:
    log.LogError('No performers found.')
    return

  os.makedirs(encoding_export_folder, exist_ok=True)

  outputDict = {}
  errorList = []

  log.LogInfo('Starting performer image export (this might take a while)')

  for performer in performers:
    log.LogProgress(count / total)

    image = face_recognition.load_image_file(urllib.request.urlopen(performer['image_path']))
    try:
      encoding = face_recognition.face_encodings(image)[0]
      outputDict[performer['id']] = encoding
    except IndexError:
      log.LogInfo(f"No face found for {performer['name']}")
      errorList.append(performer)

    count += 1

  np.savez(encodings_path, **outputDict)
  jsonPrint(errorList, errors_path)

  log.LogInfo(f'Finished exporting all {total} performer images.')
  log.LogInfo(f"Failed recognitions saved to {str(errors_path)}")

#
# Facial recognition function
#

def identify(client):
  log.LogInfo("Loading exported face encodings...")

  ids = []
  known_face_encodings = []
  npz = np.load(encodings_path)
  
  for id in npz:
    ids.append(id)
    known_face_encodings.append(npz[id])

  log.LogInfo(f"Getting images tagged with '${tag_name}'...")

  tag_id = get_scrape_tag(client)
  image_filter = {
			"tags": {
				"value": [tag_id],
				"modifier": "INCLUDES_ALL"
			}
		}

  images = client.findImages(image_filter)
  total = len(images)
  
  log.LogInfo(f"Found {total} tagged images")

  log.LogInfo('Starting identification of tagged images (this might take a while)')

  # for image in images:

  unknown_face = face_recognition.load_image_file(images[0]['path'])

  try:
    unknown_face_encoding = face_recognition.face_encodings(unknown_face)[0]
  except IndexError:
      log.LogError(f"Face not found in tagged image id {images[0]['id']}")
      return
  
  results = face_recognition.compare_faces(known_face_encodings, unknown_face_encoding)

  try:
    matching_performer_ids = [ids[i] for i in range(len(results)) if results[i] == True]

    log.LogInfo(f"Identified match! Performer ids {matching_performer_ids}")
    image_data = {
      'id': images[0]['id'],
      'performer_ids': matching_performer_ids
    }
    client.updateImage(image_data)
  except IndexError:
    log.LogError(f"No matching performer found for tagged image id {images[0]['id']}")


def get_scrape_tag(client):
  tag_id = client.findTagIdWithName(tag_name)
  if tag_id is not None:
    return tag_id
  else:
    client.createTagWithName(tag_name)
    tag_id = client.findTagIdWithName(tag_name)
    return tag_id

main()


# https://github.com/ageitgey/face_recognition
# https://github.com/ageitgey/face_recognition/issues/175