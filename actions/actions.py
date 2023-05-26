from typing import Any, Text, Dict, List
import os

path = os.path.realpath(__file__)
dir = os.path.dirname(path)
dir = dir.replace('actions', 'venv\Lib\site-packages')
os.chdir(dir)

from textblob import TextBlob
import requests
import json
import visualize
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, UserUtteranceReverted
from rasa_sdk.executor import CollectingDispatcher
from pprint import pprint

class ActionWeather(Action):

    def name(self) -> Text:
        return "action_weather"

    def run(self, dispatcher, tracker, domain):
        loc = tracker.get_slot('GPE')
        degree_sign = u'\N{DEGREE SIGN}'
        payload = {'q': loc, 'units': 'metric', 'appid': '0fc16f92e8b0caad5dfefd40fd4088da'}
        response = requests.get('http://api.openweathermap.org/data/2.5/find', params=payload)
        try:
            data = response.json()
            x = data['list'][0]
            temp = x['main']['temp']
            desc = x['weather'][0]['description']
            city = x['name']
            humidity = x['main']['humidity']
            wind_speed = x['wind']['speed']
            clouds = x['clouds']['all']
            weather_data = """It is {}{}C in {}. The humidity is {}%, wind speed is {} meter/sec, 
                cloudiness in the sky is {}%, and it is {} at the moment.""".format(
                temp, degree_sign, city, humidity, wind_speed, clouds, desc)
            dispatcher.utter_message(weather_data)
            return [SlotSet("GPE", None)]

        except requests.exceptions.HTTPError as e:
            dispatcher.utter_message(text="City not found!")

        except Exception as e:
            dispatcher.utter_message(text="Could not find the city!")


class ActionGreetName(Action):

    def name(self) -> Text:
        return "action_greet_name"

    def run(self, dispatcher, tracker, domain):

        name = tracker.get_slot('PERSON')
        if name is not None:
            dispatcher.utter_message(text="Nice to meet you, {}!".format(name))
            return [SlotSet("PERSON", None)]

        else:
            dispatcher.utter_message(text="I see , carry on !")


class ActionFeedback(Action):
    def name(self) -> Text:
        return "action_feedback"

    def run(self, dispatcher, tracker, domain):

        intent = tracker.get_intent_of_latest_message()

        if intent == "affirm":
            print("affirm")
            return [SlotSet('feedback', True)]
        elif intent == "deny":
            print("deny")
            return [SlotSet('feedback', False)]

        return []

import rasa.core
class ActionDebugger(Action):
    def name(self):
        return 'action_debugger'

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        gpe = tracker.get_slot('GPE')
        person = tracker.get_slot('PERSON')
        feedback = tracker.get_slot('feedback')

        def inspect_messages():
            latest_message = tracker.latest_message
            intent = latest_message['intent']["name"]
            entities = latest_message['entities']

            print("The user's intent is " + intent)
            if entities:
                entity_info = "The following entities were found:"
                for entity in entities:
                    entity_info += f"\n- Entity '{entity['entity']}' with value '{entity['value']}'"
                print(entity_info)
            else:
                print("No entities were found in the user message.")

        def debug_conversation():
            events = list(tracker.events)
            for event in events[-5:]:
                pprint(event)
            print("Conversation history printed to console.")

        def debug_nlu():
            nlu_data = {
                "text": tracker.latest_message['text'],
                "intent": tracker.latest_message['intent'],
                "entities": tracker.latest_message['entities']
            }
            filename = "nlu_results.json"
            # Serializing json
            json_object = json.dumps(nlu_data, indent=4)
            # Writing to nlu_results.json
            with open(filename, "w") as outfile:
                outfile.write(json_object)
            print("NLU results saved to " + filename + ".")

        def log_intent_classification():
            latest_intent_confidence = tracker.latest_message['intent']['confidence']*100
            print("Intent confidence: " + str(latest_intent_confidence) +"%")

        def user_current_mood():
            # Update the user's sentiment profile
            sentiment_profile = tracker.get_slot("sentiment_profile") or {"positive": 0, "negative": 0, "neutral": 0}
            s = "neutral"
            for i in sentiment_profile:
                if sentiment_profile[i] > sentiment_profile[s]:
                    s = i
            print(sentiment_profile)
            print("The user is in", s, "mood")

        while True:
            print("Welcome to the DEBUGGING World")
            print("1.	Inspect Messages")
            print("2.	Debug Conversation")
            print("3.	Retract User Input")
            print("4.	Debug NLU")
            print("5.	Log Intent Confidence")
            print("6.	View the user's current mood")
            print("Please select whatever you want to do")
            n = int(input())
            if n == 1:
                inspect_messages()
            elif n == 2:
                debug_conversation()
            elif n == 3:
                return [UserUtteranceReverted()]
            elif n == 4:
                debug_nlu()
            elif n == 5:
                log_intent_classification()
            elif n == 6:
                user_current_mood()
            else:
                print("Please select the correct option.")
                continue
            print("Do you want to do some more debugging:	1. Yes	2. No")
            k = int(input())
            if k == 2:
                break
        return [SlotSet('PERSON', person), SlotSet('GPE', gpe),
                SlotSet('feedback', feedback)]


class SentimentBasedUserProfiling(Action):
    path = os.path.realpath(__file__)
    dir = os.path.dirname(path)
    dir = dir.replace('actions', '')
    os.chdir(dir)
    def name(self) -> Text:
        return "action_sentiment_based_user_profiling"

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker,
            domain: Dict[Text, Any], ) -> List[Dict[Text, Any]]:
        sentence = tracker.latest_message['text']
        res = TextBlob(sentence)
        s = res.sentiment.polarity
        sentiment_profile = tracker.get_slot("sentiment_profile") or {"positive": 0, "negative": 0, "neutral": 0}
        if sentiment_profile['positive']==0 and sentiment_profile['negative']==0:
            sentiment_profile['neutral'] = 0
        if s > 0.5:
            s = "positive"
        elif s < -0.5:
            s = "negative"
        else:
            s = "neutral"
        sentiment_profile[s] += 1

        return [SlotSet("sentiment_profile", sentiment_profile)]
