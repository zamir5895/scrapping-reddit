import praw
import json
import os
import boto3
from boto3.dynamodb.types import Decimal  # Import Decimal for conversion


def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    posts_table = dynamodb.Table(os.environ['TABLE_NAME'])
    comments_table = dynamodb.Table(os.environ['TABLE_NAME2'])

    reddit = praw.Reddit(
        client_id=os.environ['CLIENT_ID'], 
        client_secret=os.environ['CLIENT_SECRET'],
        user_agent=os.environ['USER_AGENT'],
        username=os.environ['USERNAME'], 
        password=os.environ['PASSWORD']
    )

    query_params = event.get('query', {}) or {}
    topic = query_params.get('topic', 'aws')
    limit = int(query_params.get('limit', '10'))
    max_posts = limit

    posts_list = []

    try:
        print(f"Authentication successful: User {reddit.user.me()}")
    except Exception as e:
        print(f"Authentication error: {e}")
        return {
            'statusCode': 500,
            'body': {"error": "Authentication failed"}
        }

    try:
        subreddit = reddit.subreddit(topic)
        for post in subreddit.hot(limit=max_posts):
            post.comments.replace_more(limit=0)
            total_comments = len(post.comments.list())

            post_data = {
                "title": post.title,
                "upvotes": Decimal(post.score),  
                "num_comments": post.num_comments,
                "post_id": post.id,
                "url": post.url,
                "created_utc": Decimal(post.created_utc),  
                "total_comments": total_comments
            }
            posts_table.put_item(Item=post_data)

            post_data_with_comments = post_data.copy()
            post_data_with_comments["comments"] = []

            for comment in post.comments.list():
                comment_data = {
                    "post_id": post.id,
                    "comment_id": comment.id,
                    "comment_body": comment.body,
                    "comment_author": comment.author.name if comment.author else "deleted",
                    "comment_upvotes": Decimal(comment.score),  
                    "comment_created_utc": Decimal(comment.created_utc)  
                }
                comments_table.put_item(Item=comment_data)  
                post_data_with_comments["comments"].append(comment_data) 

            posts_list.append(post_data_with_comments)
            print("Single post data with comments:", json.dumps(post_data_with_comments, indent=4))

        return {
            'statusCode': 200,
            'body': posts_list,
        }

    except Exception as e:
        print(f"Error fetching posts or comments: {e}")
        return {
            'statusCode': 500,
            'body': {"error": str(e)},
        }
