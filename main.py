from flask import Flask, request, render_template, redirect, url_for
import requests
import os
import tempfile
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB file limit
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {'txt', 'json'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_profile_info(access_token):
    """Fetch Facebook profile information using access token"""
    try:
        url = "https://graph.facebook.com/me"
        params = {
            'access_token': access_token,
            'fields': 'name,id,email'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error verifying token: {str(e)}")
        return None

def process_token_file(filepath):
    """Process uploaded file containing tokens"""
    results = []
    try:
        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                try:
                    data = json.load(f)
                    tokens = data.get('tokens', [])
                except json.JSONDecodeError:
                    tokens = [line.strip() for line in f if line.strip()]
            else:
                tokens = [line.strip() for line in f if line.strip()]

            for token in tokens:
                if token:
                    profile_info = get_profile_info(token)
                    results.append({
                        'token': token,
                        'valid': bool(profile_info),
                        'profile_name': profile_info.get('name') if profile_info else "Invalid Token",
                        'profile_id': profile_info.get('id') if profile_info else None,
                        'email': profile_info.get('email') if profile_info else None
                    })
        return results
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        input_method = request.form.get('input_method', 'manual')
        
        if input_method == 'manual':
            token = request.form.get('access_token', '').strip()
            if token:
                profile_info = get_profile_info(token)
                if profile_info:
                    return render_template(
                        'result.html',
                        success=True,
                        profile_name=profile_info.get('name'),
                        profile_id=profile_info.get('id'),
                        email=profile_info.get('email'),
                        token=token[:15] + '...' if len(token) > 15 else token,
                        input_method=input_method
                    )
                return render_template(
                    'result.html',
                    error="Invalid access token",
                    input_method=input_method
                )
            return render_template(
                'result.html',
                error="Please enter an access token",
                input_method=input_method
            )
        
        elif input_method == 'file':
            if 'token_file' not in request.files:
                return render_template(
                    'result.html',
                    error="No file selected",
                    input_method=input_method
                )
            
            file = request.files['token_file']
            if file.filename == '':
                return render_template(
                    'result.html',
                    error="No file selected",
                    input_method=input_method
                )
            
            if not allowed_file(file.filename):
                return render_template(
                    'result.html',
                    error="Only .txt or .json files are allowed",
                    input_method=input_method
                )
            
            try:
                filename = secure_filename(file.filename)
                temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(temp_path)
                
                results = process_token_file(temp_path)
                os.unlink(temp_path)
                
                if not results:
                    return render_template(
                        'result.html',
                        error="No valid tokens found in file",
                        input_method=input_method
                    )
                
                valid_count = sum(1 for r in results if r['valid'])
                return render_template(
                    'result.html',
                    file_results=results,
                    valid_count=valid_count,
                    total_count=len(results),
                    input_method=input_method
                )
            
            except Exception as e:
                return render_template(
                    'result.html',
                    error=f"Error processing file: {str(e)}",
                    input_method=input_method
                )
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
