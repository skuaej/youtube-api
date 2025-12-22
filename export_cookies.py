
import os
import sys

def main():
    cookie_file = 'cookies.txt'
    if not os.path.exists(cookie_file):
        print(f"Error: {cookie_file} not found in the current directory.")
        return

    try:
        with open(cookie_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print("\n=== COPY THE CONTENT BELOW THIS LINE FOR KOYEB ENC VAR (COOKIES_TXT_CONTENT) ===\n")
        print(content)
        print("\n=== END OF CONTENT ===\n")
        print(f"Token length: {len(content)} characters.")
        
    except Exception as e:
        print(f"Error reading {cookie_file}: {e}")

if __name__ == "__main__":
    main()
