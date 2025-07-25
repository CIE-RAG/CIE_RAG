# pip install better-profanity

from better_profanity import profanity
profanity.load_censor_words()


# input: whatever text
# output: None if no profanity, else prints censored text and returns false 

def check_profanity(text):
    if profanity.contains_profanity(text):
        print("Profanity detected!")
        print(profanity.censor(text))  # You are a **** fool. 
        return True
    return False


#An extension of this would be to log these as well into chat hisotry so we can flag malicious users 
# and then restrict them 
