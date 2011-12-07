#!/usr/bin/env python

#	This file is part of G+ Tags.
#	
#	G+ Tags is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#	
#	G+ Tags is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#	
#	You should have received a copy of the GNU General Public License
#	along with G+ Tags.  If not, see <http://www.gnu.org/licenses/>.

from google.appengine.api import memcache, users
from google.appengine.ext import db, webapp
from google.appengine.ext.webapp import util, template
from google.appengine.ext.webapp.util import login_required
from oauth2client.appengine import CredentialsProperty, StorageByKeyName
from oauth2client.client import OAuth2WebServerFlow
import gdata.spreadsheet.service
import os
import pickle
import logging

FLOW = OAuth2WebServerFlow(
		client_id='883052992731.apps.googleusercontent.com',
		client_secret='FnkhZgPvl8-rhmZpaIrhpbaC',
		scope='https://www.googleapis.com/auth/plus.me',
		user_agent='gtags/1.0')

memcacheClient = memcache.Client()

class Table(object):

	def __init__(self, db, table):
		self.db = db
		self.table = table.lower()

	def get(self, kvMap):
		return self.db.get(self.table, kvMap)

	def getOne(self, kvMap):
		return self.db.getOne(self.table, kvMap)

	def getAll(self):
		return self.db.getAll(self.table)

	def update(self, kvMap, vMap):
		return self.db.update(self.table, kvMap, vMap)

	def put(self, vMap):
		return self.db.put(self.table, vMap)

	def delete(self, kvMap):
		return self.db.delete(self.table, kvMap)

class Credentials(db.Model):
	credentials = CredentialsProperty()


class MainHandler(webapp.RequestHandler):

	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'intro.html')
		self.response.out.write(template.render(path, {}))

class OAuthHandler(webapp.RequestHandler):

	@login_required
	def get(self):
		user = users.get_current_user()
		flow = pickle.loads(memcacheClient.get("oauth-%s" % user.user_id()))
		if flow:
			credentials = flow.step2_exchange(self.request.params)
			StorageByKeyName(
					Credentials, user.user_id(), 'credentials').put(credentials)
			self.redirect("/")
		else:
			pass

class ViewHandler(webapp.RequestHandler):

	def get(self):
		nick = 'wiki'
		email = 'wiki@gta.gs'
		password = 'w1k1w1k1'
		spreadsheetId = '0AntwXKY6rGRmdHAtdUlvMWR1NEpjWnNQamFYUHBzcFE'
		client = gdata.spreadsheet.service.SpreadsheetsService()
		client.email = email
		client.password = password
		client.source = nick
		spreadsheetId = spreadsheetId
		tableIdMap = {}
		tableMap = {}
		client.ProgrammaticLogin()
		feed = client.GetWorksheetsFeed(spreadsheetId)
		for entry in feed.entry:
			table = entry.title.text.lower()
			tableIdMap[table] = entry.id.text.rsplit('/', 1)[1]
			tableMap[table] = Table(self, table)
			worksheetId = tableIdMap[table]
			feed = client.GetListFeed(spreadsheetId, worksheetId)
			results = []
			for entry in feed.entry:
				logging.info(len(feed.entry))
				results.append((dict((v.column, v.text) for v in entry.custom.values())))
			path = os.path.join(os.path.dirname(__file__), 'view.html')
			self.response.out.write(template.render(path, {'results':results}))

class SubmitHandler(webapp.RequestHandler):

	@login_required
	def get(self):
		user = users.get_current_user()
		credentials = StorageByKeyName(Credentials, user.user_id(), 'credentials').get()
		if credentials is None or credentials.invalid == True:
			callback = self.request.relative_url('/oauth2callback')
			authorize_url = FLOW.step1_get_authorize_url(callback)
			memcacheClient.set("oauth-%s" % user.user_id(), pickle.dumps(FLOW))
			self.redirect(authorize_url)
		else:
			path = os.path.join(os.path.dirname(__file__), 'input.html')
			self.response.out.write(template.render(path, {}))
	
	def post(self):
		user = users.get_current_user()
		credentials = StorageByKeyName(
				Credentials, user.user_id(), 'credentials').get()

		if credentials is None or credentials.invalid == True:
			self.response.set_status(403)
			self.response.out.write("403 Not Authorized")
		else:
			# TODO: process some data here
			self.response.set_status(501)
			self.response.out.write("501 Not implemented")

def main():
	application = webapp.WSGIApplication(
			[
			('/submit', SubmitHandler),
			('/published', ViewHandler),
			('/oauth2callback', OAuthHandler),
			('/', MainHandler)
			],
			debug=True)
	util.run_wsgi_app(application)

if __name__ == '__main__':
	main()
