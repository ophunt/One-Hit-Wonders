#!/anaconda2/envs/one_hit_wonders/bin/python python3

# Import libs
import re
import requests
import timeit
import csv
import asyncio
from bs4 import BeautifulSoup, Comment

# Class to store songs
class Song:
	def __init__(self, name, date, artists):
		self.name = name
		self.date = date
		self.artists = artists

	def __eq__(self, other):
		return self.name == other.name \
		   and self.date == other.date \
		   and self.artists == other.artists

	def __hash__(self):
		return hash((self.name, self.date, *self.artists))

# Takes a URL and returns the BS4 soup of it
def get_soup(session, url):
	# Get the page with a reasonable timeout
	result = session.get(url)
	# Store the HTML content of the page
	page = result.content
	# Soup the HTML content and return it
	return BeautifulSoup(page, "html.parser")

# Takes a soup of a page and returns the table of hits
def get_table(soup):
	# Get a list of all the comments
	comments = soup.find_all(string=lambda text:isinstance(text, Comment))
	# Find the comment that immediately precedes the table of songs
	for c in comments:
		if c == " Display Chart Table ":
			return c.findNext("table")

# Get the URL of the next page
def get_link(soup):
	# Get a list of all the comments
	comments = soup.find_all(string=lambda text:isinstance(text, Comment))
	# Find the comment that immediately precedes the table of links
	for c in comments:
		if c == " Previous / Next ":
			# Find the a tag with link to next page
			a = c.findNext("td").findNext("td").findNext("a")
			# Get the href of it
			if a == None:
				return None
			else:
				href = a["href"]
				return href

# Takes the table and returns the important rows of it
def parse_table(table):
	table_rows = table.findChildren("tr", recusive=False)
	return table_rows[2:]

# Go through each row and put songs in the table
def parse_rows(table_rows, songs, art_re):
	for row in table_rows:
		# Get the song info out of the row
		song_num, song_name, song_date, song_artists = parse_table_row(row, art_re)
		# Only parse the top 40
		if song_num > 40:
			break
		# Create a Song from the row
		song = Song(song_name, song_date, song_artists)
		# Add the song to the set of songs
		songs.add(song)

# Takes the row in a table and get all the song info we need from it
def parse_table_row(row, art_re):
	cells = row.findChildren("td", recusive=False)
	song_name = cells[4].findChildren("b")[0].text
	song_num = int(cells[0].text.strip())
	song_date = cells[5].text.strip()
	song_artists_str = cells[4].text.replace(song_name, "").strip()
	song_artists = parse_artists(song_artists_str, art_re)
	return song_num, song_name, song_date, song_artists

# Take the string of all artists and split it up into the actual individual artists
def parse_artists(str, art_re):
	raw_artists = re.split(art_re, str)
	artists = [s.strip() for s in raw_artists]
	return artists

if __name__ == "__main__":
	# Start a timer to track time
	start = timeit.default_timer()

	# Set to store all songs
	songs = set([])

	# Dict to store count of songs for each artist
	artists = {}

	# Create a RegEx to split up multiple artists on the same song
	art_delimiters = [",", "/", "&", "featuring", "feat", "with"]
	delim_pattern = "|".join(map(re.escape, art_delimiters))
	art_regex = re.compile(delim_pattern)

	# Create a request connection to improve connection speed
	s = requests.Session()

	# Store the first URL
	BASE_URL = "http://www.umdmusic.com/"
	START_URL = "http://www.umdmusic.com/default.asp?Lang=English&Chart=D&ChDate=19400727&ChMode=P"

	# Set initial value for URL
	cur_URL = START_URL
	pages = 0

	#for i in range(50):
	while True:
		# Keep track of where we are:
		print(cur_URL)
		# Keep track of how many pages we've done
		pages += 1

		# Take a URL and get the soup of it
		cur_soup = get_soup(s, cur_URL)
		# Get the next page link from the soup
		next_link = get_link(cur_soup)
		# Get the rows of the table from the soup
		cur_chart_table = get_table(cur_soup)
		cur_table_rows = parse_table(cur_chart_table)
		parse_rows(cur_table_rows, songs, art_regex)

		# Check if we're done
		if next_link == None:
			break
		# Set the URL to the URL of the next page, and continue to it
		cur_URL = BASE_URL + next_link
		continue

	# Go through the set of songs and add 1 to song count of each artist on the song
	for s in songs:
		for a in s.artists:
			if a in artists:
				artists[a] += 1
			else:
				artists[a] = 1

	print(artists)

	with open("artists.csv", "w") as f:
		w = csv.writer(f)
		w.writerow(["Name", "Hits"])
		w.writerows(artists.items())

	stop = timeit.default_timer()
	t_delta = stop-start
	print("Time: ", t_delta)
	print("Per page: ", t_delta / pages)
