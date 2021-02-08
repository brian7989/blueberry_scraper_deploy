import csv
import os

from flask import Flask, render_template, request, redirect, send_from_directory
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

jobSites = [
    "https://weworkremotely.com/",
    "https://stackoverflow.com/jobs",
    "https://remoteok.io/"
]

# Headers to resolve bad request errors
headers = {
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
}

# Fake Database
db = {}


# Scrape WWR jobs
def wwr(keyword):
    print("------- WWR -------")
    res = requests.get(f"https://weworkremotely.com/remote-jobs/search?term={keyword}")
    wwrJobs = BeautifulSoup(res.text, "html.parser").find("article").find("ul").find_all("li")
    jobsArray = []
    for j in wwrJobs:
        try:
            jobTitle = j.find("span", {"class": "title"}).text
            company = j.find("span", {"class": "company"})
            companyName = company.text
            jobURL = "https://www.weworkremotely.com" + company.parent.attrs["href"]
            logo = j.find("div", {"class": "flag-logo"})
            logoURL = logo.attrs["style"][21:-1] if logo is not None else "https://cdn.onlinewebfonts.com/svg/img_355049.png"
            jobObj = {"logoURL": logoURL, "jobURL": jobURL, "jobTitle": jobTitle, "companyName": companyName}
            jobsArray.append(jobObj)
        except Exception as e:
            print(f"ERROR: {e} \n")
            pass
    db[keyword]["wwr"] = jobsArray


# Scrape RemoteOK jobs
def remoteok(keyword):
    print("------- RemoteOk -------")
    res = requests.get(f"https://remoteok.io/remote-dev+{keyword}-jobs", headers=headers)
    try:
        remoteokJobs = BeautifulSoup(res.text, "html.parser").find("div",{"class": "container"}).find_all("tr")
    except AttributeError:
        db[keyword]["remoteok"] = []
        return True
    jobsArray = []
    for t in remoteokJobs:
        try:
            jobTitle = t.find("h2", {"itemprop": "title"}).text
            jobURL = "https://www.remoteok.io" + t.find("a", {"itemprop": "url"}).attrs["href"]
            companyName = t.find("h3", {"itemprop": "name"}).text
            logoURL = t.find("img", {"class": "logo"})
            logoURL = logoURL.attrs["src"] if logoURL is not None else "https://cdn.onlinewebfonts.com/svg/img_355049.png"
            jobObj = {"logoURL": logoURL, "jobURL": jobURL, "jobTitle": jobTitle, "companyName": companyName}
            jobsArray.append(jobObj)
        except Exception:
            pass
    db[keyword]["remoteok"] = jobsArray
    return False


# Scrape Stack Overflow Jobs
def stackOverFlow(keyword):
    print("------- Stack OverFlow -------")
    res = requests.get(f"https://stackoverflow.com/jobs?r=true&q={keyword}")
    soup = BeautifulSoup(res.text, "html.parser")
    jobNum = int(soup.find("span", {"class", "description"}).text[2])
    if jobNum == 0:
        db[keyword] = {'stackoverflow': []}
        return True
    stackJobs = soup.find_all("div", {"class": "-job"})
    jobsArray = []
    for j in stackJobs:
        try:
            a = j.find("a", {"class": "s-link"})
            jobTitle = a.text
            jobURL = "https://www.stackoverflow.com" + a.attrs["href"]
            logoURL = j.find("img").attrs["src"]
            companyName = j.find("h3", {"class": "fc-black-700"}).find("span").text
        except Exception as e:
            print(f"ERROR: {e} \n")
            pass
        jobObj = {"logoURL": logoURL, "jobURL": jobURL, "jobTitle": jobTitle, "companyName": companyName}
        jobsArray.append(jobObj)
    db[keyword] = {"stackoverflow": jobsArray}
    return False


# Save db[keyword] as CSV
def saveToCSV(keyword):
    try:
        os.mkdir("./csv_storage")
    except OSError:
        print("Directory exists")
    if not os.path.exists(os.path.join(f"./csv_storage/{keyword}", ".csv")):
        print(f"Generating new CSV for {keyword}...")
        with open("./csv_storage/" + keyword + ".csv", mode="w") as f:
            writer = csv.writer(f)
            writer.writerow(["Company", "Job", "Link", "Source"])
            for source in db[keyword]:
                for job in db[keyword][source]:
                    writer.writerow([job["companyName"],
                                     job["jobTitle"],
                                     job["jobURL"],
                                     source])


# Main Screen
@app.route('/')
def main():
    return render_template("index.html")


# Display scrape results
@app.route('/jobs')
def jobs():
    try:
        userInput = request.args.get("job")
        if not userInput:
            raise ValueError()
        userInput = userInput.lower()
        # First searches local database, then scrapes web
        if userInput not in db:
            stackOverFlowZero = stackOverFlow(userInput)
            wwr(userInput)
            remoteOkZero = remoteok(userInput)
            # If remoteOk and StackOverflow return 0 jobs, set wwr to 0 jobs
            if stackOverFlowZero and remoteOkZero:
                db[userInput]["wwr"] = []
        return render_template("jobs.html", db=db, userInput=userInput)
    except ValueError as e:
        print("Invalid Query: ", e)
        return redirect("/")


# Export CSV
@app.route('/export')
def export():
    try:
        fileName = request.args.get("keyword")
        if not fileName:
            raise Exception
        fileName = fileName.lower()
        if fileName not in db:
            raise Exception
        # Save and export CSV.
        saveToCSV(fileName)
        return send_from_directory("./csv_storage", f"{fileName}.csv", as_attachment=True)
    except Exception as e:
        print(e)
        return redirect("/")


if __name__ == '__main__':
    app.run()
