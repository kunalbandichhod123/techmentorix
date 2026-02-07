# techmentorix
this is an open innovation repo 


<!-- activate the conda by :  -->
go to cd techmentorix
conda activate venv/

<!-- THIS IS THE SMART CHAT AND VOICE ASSISTANT FOR AYURVEDA RELATED ANY QUERIES  -->
###           VEDABUDDY          ###
# Project contents 
one frontend and one backend folder

# Run Simple Streamlit UI 
1) install all dependencies through 
    pip install -r requirements.txt

2) activate the venv : 
    run -> conda activate venv/

3) change the directory to core folder by running :
    cd "BACKEND\core"

4) Run the project fromm streamlit UI 
    streamlit run app.py

# Run Advance and aesthetic UI 
 
 * NOTE : Make sure you have node installed in your pc check through(bash) : node -v
    if not then download by (bash) : npm -v

1) Change The Directory to FRONTEND\vedabuddy complete ui\ayur-voice-guide-main by running : 
    cd "FRONTEND\vedabuddy complete ui\ayur-voice-guide-main"

2) install all dependencies by : 
    run -> npm install

 * Description : This command reads the package.json file, downloads all required packages, and places them in the node_modules folder. 

3) If your frontend folder does not have folder named dist then run this command : 
    npm run build

* Description : This will create a new folder named dist inside ayur-voice-guide-main. This dist folder is what we will serve via FastAPI.

4) Go back to your main folder by : 
    cd../../..

5) Then go inside the core folder from BACKEND : 
    cd "BACKEND\core"

6) Run the final code file : 
    python main.py

* Description : This is our main FASTAPI code file 
