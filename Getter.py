import praw
import sys
import time
import os
import pafy #https://pypi.python.org/pypi/pafy
import boto3
import boto #can be used side by side with boto3
from urllib.parse import urlparse
import json
import io
from pydub import AudioSegment
from credentials import AWS_ACCESS_KEY, AWS_BUCKET_NAME, AWS_SECRET_KEY, CLIENT_ID, CLIENT_SECRET, USER_AGENT

#gain authorization to scan reddit through praw
reddit = praw.Reddit(client_id= CLIENT_ID,
                     client_secret=CLIENT_SECRET,
                     user_agent= USER_AGENT)

counter = 0
#holds titles of songs
titles = []
#holds urls of songs
urls = []
#loop that gets titles and urls of songs
for submission in reddit.subreddit('music').top('day'):
    if counter == 3:
        break
    elif (('youtube.com' in submission.url ) or ('youtu.be' in submission.url)):
        print("Video title: " + submission.title.encode(sys.stdout.encoding, errors='ignore').decode('UTF-8', errors='ignore'))
        titles.append(submission.title.encode(sys.stdout.encoding, errors='ignore').decode('UTF-8', errors='ignore'))
        print("Video url: " + submission.url + "\n")
        urls.append(submission.url)
        counter = counter + 1

counter = 0

#writes the url and title of the video in a text file in the history directory
with open("alexa/history/" + time.strftime("%d.%m.%Y") + '.txt', 'w') as f:
    for title in titles:
        f.write(urls[counter] + '\n')
        counter += 1

#clears music directory
counter = 0
while counter < 3:
    for f in os.listdir("alexa/music/" + str(counter)):
        print('Removing: ' + f + " from music")
        os.remove('alexa/music/' + str(counter) + "/" + f)
    counter += 1

print("\n")

#clears converted directory
counter = 0
while counter < 3:
    for f in os.listdir("alexa/converted/"+ str(counter)):
        print('Removing: ' + f + " from converted")
        os.remove('alexa/converted/' + str(counter) + "/" + f)
    counter += 1

print("\n")

#list to be converted to json file
ytlist = []
counter = 0

#loop that downloads the song in webm format and appends the necessary information to the list for the json file
for url in urls:
    try:
        video = pafy.new(urlparse(url).query[2:])
        bestaudio = video.getbestaudio(preftype = 'webm')
        print("Downloading: "+ video.title)
        bestaudio.download(filepath="alexa/music/" + str(counter))
        url = 1
        counter += 1
        #catches errors and ignores the song if error occurs
    except Exception as e:
        print('Something went wrong... Ignoring this link.')
        print(e)
        url = 0
        counter += 1

print("\n")

#sets converter to ffmpeg
AudioSegment.converter = "C:/ffmpeg/bin/ffmpeg.exe"

#converting webm to mp3
counter = 0
while counter < 3: 
    for f in os.listdir("alexa/music/" + str(counter)):
        print("Converting " + f + "...")
        #splices only the first ten minutes of the song
        first_ten = AudioSegment.from_file("C:/Users/Wearable/Desktop/redditMusic/alexa/music/" + str(counter) + "/" + f, format = "webm")[:600*1000]
        first_ten.export("C:/Users/Wearable/Desktop/redditMusic/alexa/converted/" + str(counter) + "/" + f[:-4] + "mp3", format="mp3")
        print("Conversion successful.")
    counter += 1

print()

#checks for version control
try:
    to_unicode = unicode
except NameError:
    to_unicode = str

# Let's use Amazon S3
client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
  )
print("Opening client and empyting bucket.")

def empty_s3_bucket(client):
    # empty existing bucket
    response = client.list_objects_v2(Bucket=AWS_BUCKET_NAME)
    if 'Contents' in response:
        for item in response['Contents']:
            print('deleting file', item['Key'])
            client.delete_object(Bucket=AWS_BUCKET_NAME, Key=item['Key'])
            while response['KeyCount'] == 1000:
                response = client.list_objects_v2(
                Bucket=AWS_BUCKET_NAME,
                StartAfter=response['Contents'][0]['Key'],
                )
                for item in response['Contents']:
                    print('deleting file', item['Key'])
                    client.delete_object(Bucket=AWS_BUCKET_NAME, Key=item['Key'])

#clearing bucket of previous items
empty_s3_bucket(client)
print("\n")
print("Bucket emptying successful. \n")
#uploading converted music to s3

counter = 0
while counter < 3:
    for f in os.listdir("alexa/converted/" + str(counter)):
        print("Uploading " + f + " to S3...")
        client.upload_file("alexa/converted/" + str(counter) + "/" + f, AWS_BUCKET_NAME, f.replace('/', ' '))
    counter += 1
print('File upload success.')


con = boto.connect_s3(AWS_ACCESS_KEY, AWS_SECRET_KEY)
bucket=con.get_bucket(AWS_BUCKET_NAME)
counter = 0
orderedList = sorted(bucket.get_all_keys(), key=lambda k: k.last_modified)
for key in orderedList:
    #format of time: "yyyy-MM-dd'T'HH:mm:ss'.0Z'"
    date = time.strftime("%Y-%m-%dT%H:%M:%S.0Z")
    ytlist.append({'uid':counter,'updateDate':date,'titleText':key.name[:-4],'mainText':"",'streamUrl':key.generate_url(query_auth = False, expires_in = 0)})
    counter += 1

# Write JSON file
with io.open('data.json', 'w', encoding='utf8') as outfile:
    print("Writing to JSON file...")
    str_ = json.dumps(ytlist,
                      indent=4, sort_keys=True,
                      separators=(',', ': '), ensure_ascii=False)
    outfile.write(to_unicode(str_))

    print("Write successful. \n")
client.upload_file("data.json", AWS_BUCKET_NAME, 'musicData.json')

#clears music directory
counter = 0
while counter < 3:
    for f in os.listdir("alexa/music/" + str(counter)):
        print('Removing: ' + f + " from music")
        os.remove('alexa/music/' + str(counter) + "/" + f)
    counter += 1

print("\n")

#clears converted directory
counter = 0
while counter < 3:
    for f in os.listdir("alexa/converted/"+ str(counter)):
        print('Removing: ' + f + " from converted")
        os.remove('alexa/converted/' + str(counter) + "/" + f)
    counter += 1

print()
print("Script done.")