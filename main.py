import tweepy
import os
import requests
import time
import json
import re
from datetime import datetime, timedelta
from textblob import TextBlob
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RugGuardBot:
    def __init__(self):
        load_dotenv()
        self.setup_client()
        self.trigger_phrase = "riddle me this"
        self.processed_tweets = set()
        self.trusted_accounts = self.load_trusted_accounts()
        
    def setup_client(self):
        """Initialize Twitter API client"""
        # Check required credentials
        bearer_token = os.getenv('X_BEARER_TOKEN')
        api_key = os.getenv('X_API_KEY')
        api_secret = os.getenv('X_API_KEY_SECRET')
        access_token = os.getenv('X_ACCESS_TOKEN')
        access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        
        if not bearer_token:
            raise ValueError("X_BEARER_TOKEN is required for searching tweets")
        if not all([api_key, api_secret, access_token, access_token_secret]):
            raise ValueError("All OAuth 1.0a credentials (API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET) are required for posting replies")
        
        self.client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            wait_on_rate_limit=True
        )
        
        # Test authentication
        try:
            me = self.client.get_me()
            logger.info(f"✅ Authenticated as: @{me.data.username}")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            logger.error("Make sure all 5 credentials are set correctly")
            raise
    
    def load_trusted_accounts(self):
        """Load trusted accounts list from GitHub"""
        try:
            url = "https://raw.githubusercontent.com/devsyrem/turst-list/main/list"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            trusted_list = []
            for line in response.text.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    username = line.replace('@', '').strip().lower()
                    if username:
                        trusted_list.append(username)
            
            logger.info(f"✅ Loaded {len(trusted_list)} trusted accounts")
            return set(trusted_list)  # Use set for faster lookups
            
        except requests.RequestException as e:
            logger.error(f"❌ Failed to load trusted accounts: {e}")
            return set()
    
    def search_and_analyze_single_trigger(self):
        """OPTIMIZED: Single API call to find and analyze trigger mentions"""
        try:
            # Single comprehensive API call with all needed expansions
            tweets = self.client.search_recent_tweets(
                query=f'"{self.trigger_phrase}" -is:retweet',  # Exclude retweets
                max_results=10,  # Get multiple to find valid ones
                tweet_fields=['author_id', 'created_at', 'text', 'in_reply_to_user_id', 'referenced_tweets', 'conversation_id'],
                expansions=['author_id', 'referenced_tweets.id', 'referenced_tweets.id.author_id', 'in_reply_to_user_id'],
                user_fields=['username', 'created_at', 'description', 'verified', 'public_metrics']
            )
            
            if not tweets.data:
                logger.info("No tweets found with trigger phrase")
                return None
            
            # Build user lookup from includes
            users_dict = {}
            if hasattr(tweets, 'includes') and tweets.includes and 'users' in tweets.includes:
                for user in tweets.includes['users']:
                    users_dict[user.id] = user
            
            # Find valid trigger replies and process
            for tweet in tweets.data:
                if (tweet.id in self.processed_tweets or 
                    not tweet.referenced_tweets or 
                    self.trigger_phrase.lower() not in tweet.text.lower()):
                    continue
                
                # Find the original tweet being replied to
                original_tweet_id = None
                original_author_id = None
                
                for ref_tweet in tweet.referenced_tweets:
                    if ref_tweet.type == 'replied_to':
                        original_tweet_id = ref_tweet.id
                        # Get author from referenced tweets in includes
                        if hasattr(tweets, 'includes') and tweets.includes and 'tweets' in tweets.includes:
                            for included_tweet in tweets.includes['tweets']:
                                if included_tweet.id == ref_tweet.id:
                                    original_author_id = included_tweet.author_id
                                    break
                        break
                
                if not original_author_id or original_author_id not in users_dict:
                    continue
                
                # Mark as processed
                self.processed_tweets.add(tweet.id)
                
                # Analyze using data we already have
                original_author = users_dict[original_author_id]
                analysis = self.analyze_account_from_data(original_author)
                
                # Generate and post report
                report = self.generate_trustworthiness_report(analysis)
                success = self.post_reply(tweet.id, report)
                
                if success:
                    logger.info(f"✅ Successfully processed trigger for @{original_author.username}")
                    return True
                else:
                    logger.warning(f"❌ Failed to post reply for @{original_author.username}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error in search_and_analyze_single_trigger: {e}")
            return None
    
    def analyze_account_from_data(self, user_data):
        """Analyze account using data already fetched"""
        try:
            # Extract metrics from public_metrics
            public_metrics = getattr(user_data, 'public_metrics', {})
            followers_count = public_metrics.get('followers_count', 0)
            following_count = public_metrics.get('following_count', 0)
            tweet_count = public_metrics.get('tweet_count', 0)
            
            analysis = {
                'username': user_data.username,
                'account_age_days': self.calculate_account_age(user_data.created_at),
                'follower_following_ratio': self.calculate_follower_ratio(followers_count, following_count),
                'bio_analysis': self.analyze_bio(getattr(user_data, 'description', '') or ""),
                'is_verified': getattr(user_data, 'verified', False),
                'tweet_count': tweet_count,
                'followers_count': followers_count,
                'following_count': following_count,
                'engagement_metrics': {'avg_likes': 0, 'avg_retweets': 0, 'avg_replies': 0, 'engagement_rate': 0},
                'content_sentiment': {'sentiment': 'neutral', 'polarity': 0, 'subjectivity': 0}
            }
            
            # Simplified trust network check
            analysis['trust_network_score'] = self.check_trust_network_simple(user_data.username)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing account data: {e}")
            return None
    
    def calculate_account_age(self, created_at):
        """Calculate account age in days"""
        try:
            if not created_at:
                return 0
            
            if isinstance(created_at, str):
                # Handle different datetime formats
                created_at = created_at.replace('Z', '+00:00')
                created_dt = datetime.fromisoformat(created_at)
            else:
                created_dt = created_at
            
            # Make timezone-aware if needed
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
            
            return (datetime.now(created_dt.tzinfo) - created_dt).days
        except Exception as e:
            logger.error(f"Error calculating account age: {e}")
            return 0
    
    def calculate_follower_ratio(self, followers, following):
        """Calculate follower to following ratio"""
        if not followers or not following:
            return 0
        if following == 0:
            return float('inf') if followers > 0 else 0
        return followers / following
    
    def analyze_bio(self, bio):
        """Analyze user bio for patterns"""
        if not bio:
            return {'length': 0, 'has_crypto_keywords': False, 'has_links': False}
        
        crypto_keywords = ['crypto', 'bitcoin', 'eth', 'nft', 'defi', 'web3', 'blockchain', 'token', 'coin', 'solana']
        link_pattern = r'http[s]?://[^\s]+'
        
        return {
            'length': len(bio),
            'has_crypto_keywords': any(keyword in bio.lower() for keyword in crypto_keywords),
            'has_links': bool(re.search(link_pattern, bio))
        }
    
    def check_trust_network_simple(self, username):
        """Simplified trust network check - check if username is in trusted list"""
        # Direct check if user is in trusted list
        if username.lower() in self.trusted_accounts:
            return 5  # High trust score for being directly in trusted list
        
        # For now, return 0 - in production you'd need additional API calls
        # to check followers, which we're avoiding to minimize API usage
        return 0
    
    def generate_trustworthiness_report(self, analysis):
        """Generate a concise trustworthiness report"""
        if not analysis:
            return "❌ Unable to analyze account"
        
        username = analysis['username']
        trust_score = 0
        risk_factors = []
        positive_factors = []
        
        # Account age scoring
        age_days = analysis['account_age_days']
        if age_days > 365:
            trust_score += 2
            positive_factors.append("Established account")
        elif age_days > 90:
            trust_score += 1
            positive_factors.append("Mature account")
        elif age_days < 30:
            risk_factors.append("Very new account")
        
        # Follower ratio scoring
        ratio = analysis['follower_following_ratio']
        if ratio == float('inf'):
            trust_score += 1
            positive_factors.append("Many followers, following few")
        elif 0.1 <= ratio <= 10:
            trust_score += 1
            positive_factors.append("Balanced follow ratio")
        elif ratio > 100:
            positive_factors.append("High follower ratio")
        elif ratio < 0.01:
            risk_factors.append("Following many, few followers")
        
        # Trust network scoring
        trust_network = analysis['trust_network_score']
        if trust_network >= 5:
            trust_score += 3
            positive_factors.append("Verified trusted account")
        elif trust_network >= 2:
            trust_score += 2
            positive_factors.append("Trusted connections")
        else:
            risk_factors.append("No verified trust connections")
        
        # Verification bonus
        if analysis['is_verified']:
            trust_score += 1
            positive_factors.append("Verified account")
        
        # Bio analysis
        bio = analysis['bio_analysis']
        if bio['length'] > 20:
            trust_score += 0.5
        if bio['has_crypto_keywords'] and bio['length'] < 30:
            risk_factors.append("Minimal crypto bio")
        
        # Large following bonus
        if analysis['followers_count'] > 10000:
            trust_score += 0.5
            positive_factors.append("Large following")
        
        # Determine assessment
        if trust_score >= 5:
            assessment = "🟢 LIKELY TRUSTWORTHY"
        elif trust_score >= 3:
            assessment = "🟡 PROCEED WITH CAUTION"
        else:
            assessment = "🔴 HIGH RISK"
        
        # Build concise report (Twitter character limit friendly)
        report_lines = [
            f"🔍 @{username}",
            f"{assessment} ({trust_score:.1f}/7)",
            f"📅 {age_days}d old | 👥 {analysis['followers_count']:,}F/{analysis['following_count']:,}F"
        ]
        
        if positive_factors:
            report_lines.append("✅ " + ", ".join(positive_factors[:2]))
        
        if risk_factors:
            report_lines.append("⚠️ " + ", ".join(risk_factors[:2]))
        
        return "\n".join(report_lines)
    
    def post_reply(self, reply_to_tweet_id, report):
        """Post the trustworthiness report as a reply"""
        try:
            response = self.client.create_tweet(
                text=report,
                in_reply_to_tweet_id=reply_to_tweet_id
            )
            
            if response.data:
                logger.info(f"✅ Posted reply: {response.data['id']}")
                return True
            else:
                logger.error("❌ Failed to post reply - no response data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error posting reply: {e}")
            return False
    
    def run_once(self):
        """Run one cycle of the bot - OPTIMIZED for minimal API calls"""
        logger.info("🔄 Running optimized bot cycle...")
        
        try:
            result = self.search_and_analyze_single_trigger()
            if result:
                logger.info("✅ Successfully processed a trigger")
            else:
                logger.info("ℹ️ No valid triggers found or processed")
                
        except Exception as e:
            logger.error(f"❌ Error in bot cycle: {e}")
    
    def run_continuous(self, check_interval=600):
        """Run the bot continuously with longer intervals to preserve API limits"""
        logger.info(f"🚀 Starting RugGuard Bot (checking every {check_interval} seconds)")
        
        while True:
            try:
                self.run_once()
                logger.info(f"💤 Sleeping for {check_interval} seconds...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error: {e}")
                logger.info("🔄 Retrying in 5 minutes...")
                time.sleep(300)

def main():
    """Main function to run the bot"""
    try:
        bot = RugGuardBot()
        
        # Check environment variable for run mode
        if os.getenv('RUN_ONCE', '').lower() == 'true':
            logger.info("🔧 Running in single-cycle mode")
            bot.run_once()
        else:
            logger.info("🔄 Running in continuous mode")
            # Increased interval to preserve API limits (10 minutes)
            bot.run_continuous(check_interval=600)
            
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()