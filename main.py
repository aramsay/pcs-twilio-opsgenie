# phoneduty
# Dispatch incoming telephone voicemails/SMS messages from Twilio according to a PagerDuty on-call schedule
# Modified to now work with OpsGenie instead for SMS messages

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import json
import logging
import urllib2
import urlparse

# Shorten MP3 URL for SMS length limits
#def shorten(url):
#    gurl = 'https://www.googleapis.com/urlshortener/v1/url'
#    data = json.dumps({'longUrl': url})
#    request = urllib2.Request(gurl, data, {'Content-Type': 'application/json'})
#    try:
#		f = urllib2.urlopen(request)
#		results = json.load(f)
#	except urllib2.HTTPError, e: # triggers on HTTP code 201
#		logging.warn(e.code)
#		error_content = e.read()
#		results = json.JSONDecoder().decode(error_content)
#	return results['id']

# Outbput TwilML to record a message and pass it to the RecordHandler
class CallHandler(webapp.RequestHandler):
    def get(self):
	logging.info('Recieved call: ' + self.request.query_string)

        # Set service key
	if (self.request.get("service_key")):
	    service_key = self.request.get("service_key")
	    logging.debug("service_key = \"" + service_key + "\"")
	else:
	    logging.error("No service key specified")

        # Set greeting
        if (self.request.get("greeting")):
            greeting = self.request.get("greeting")
            logging.debug("greeting = \"" + greeting + "\"")
        else:
            logging.info("Using default greeting")
            greeting = "Leave a message to contact the on call staff."
        
        # Determine the RecordHandler URL to use based on the current base URL
        o = urlparse.urlparse(self.request.url)
        recordURL = urlparse.urlunparse((o.scheme, o.netloc, 'record?service_key=' + service_key, '', '', ''))
	logging.debug("recordURL = \"" + recordURL + "\"")

        response = (
            "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>"
            "<Response>"
            "        <Say>" + greeting + "</Say>"
            "        <Record action=\"" + recordURL + "\" method=\"GET\"/>"
            "        <Say>I did not receive a recording.</Say>"
            "</Response>")
	logging.debug("response = \"" + response + "\"")
        self.response.out.write(response)

# Open a PagerDuty incident based on an SMS message
class SMSHandler(webapp.RequestHandler):
    def get(self):
	logging.info('Received SMS: ' + self.request.query_string)

        # Set service key
	if (self.request.get("service_key")):
	    service_key = self.request.get("service_key")
	    logging.debug("service_key = \"" + service_key + "\"")
	else:
	    logging.error("No service key specified")
	    
	msg_body = self.request.get("Body")
	msg_body = msg_body.replace("\r"," ")
	msg_body = msg_body.replace("\n"," ")
	
	msg_body_summary = msg_body
	    
	msg_from = self.request.get("From")
	msg_from = msg_from.replace("\r"," ")
	msg_from = msg_from.replace("\n"," ")
	    
       # incident = '{"service_key": "%s","incident_key": "%s","event_type": "trigger","description": "%s %s"}'%(service_key,self.request.get("From"),msg_from,msg_body)
	
	incident = '{"apiKey":"%s","message":"%s","teams":"technical","source":"%s","note":"%s"}'%(service_key,msg_body_summary,msg_from,msg_body)
		
        try:
           	results = urllib2.urlopen("https://api.opsgenie.com/v1/json/alert", incident)
           	logging.debug(incident)
           	logging.debug(results)
        except urllib2.HTTPError, e:
            logging.warn( e.code )
        except urllib2.URLError, e:
            logging.warn(e.reason)     

# Shorten the URL and trigger a PagerDuty incident
class RecordHandler(webapp.RequestHandler):
    def get(self):
        logging.info('Received recording: ' + self.request.query_string)

        # Set service key
	if (self.request.get("service_key")):
	    service_key = self.request.get("service_key")
	    logging.debug("service_key = \"" + service_key + "\"")
	else:
	    logging.error("No service key specified")

        recUrl = self.request.get("RecordingUrl")
        phonenumber = self.request.get("From")

        response = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<Response><Say>Thank you. We are now directing your message to the on call staff. Goodbye.</Say>"
                "</Response>")
        self.response.out.write(response)

        if(recUrl):
	    logging.debug('Recording URL: ' + recUrl)
            recUrl = recUrl + '.mp3' # Append .mp3 to improve playback on more devices
        else:
	    logging.warn('No recording URL found')
            recUrl = ""

	#shrten = "Error"
    #    try:
    #        shrten = shorten(recUrl)
    #    except urllib2.HTTPError, e:
    #        shrten = "HTTPError"
    #        logging.warn( e.code )
    #    except urllib2.URLError, e:
    #        shrten = "URLError"
    #        logging.warn(e.reason) 
    #    
    #    logging.info('Shortened to: ' + shrten)
    
	shrten = recUrl
	
        #incident = '{"service_key": "%s","incident_key": "%s","event_type": "trigger","description": "%s %s"}'%(service_key,shrten,shrten,phonenumber)
        incident = '{"apiKey":"%s","message":"%s","teams":"technical","source":"%s","note":"%s"}'%(service_key,shrten,phonenumber,shrten)
        try:
            results = urllib2.urlopen("https://api.opsgenie.com/v1/json/alert", incident)
            logging.debug(incident)
            logging.debug(results)
        except urllib2.HTTPError, e:
            logging.warn( e.code )
        except urllib2.URLError, e:
            logging.warn(e.reason)     

# A somewhat descriptive index page
class IndexHandler(webapp.RequestHandler):
    def get(self):
        response = (
                "<html>"
                "<h1>OpsGenie SMS gateway</h1>"
		"<p><This is the PCS Twilio OpsGenie Voice/SMS gateway</a></p>"
                "</html>")
        self.response.out.write(response)

app = webapp.WSGIApplication([
    ('/call', CallHandler),
    ('/record', RecordHandler),
    ('/sms', SMSHandler),
    ('/', IndexHandler)],
    debug=True)
