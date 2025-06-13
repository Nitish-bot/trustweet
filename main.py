import tweepy
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    
    BEARER_TOKEN = os.getenv('X_BEARER_TOKEN')
    API_KEY = os.getenv('X_API_KEY')
    API_SECRET = os.getenv('X_API_KEY_SECRET')
    ACCESS_TOKEN = os.getenv('X_ACCESS_TOKEN')
    ACCESS_TOKEN_SECRET = os.getenv('X_ACCESS_TOKEN_SECRET')

    TRIGGER_QUERY = "riddle me this"
    CASE_SENSITIVE = False

    print(BEARER_TOKEN)

    client = tweepy.Client(bearer_token=BEARER_TOKEN)

    tweets_with_query = client.search_recent_tweets(query=TRIGGER_QUERY)

    print(tweets_with_query)



if __name__ == "__main__":
    main()
