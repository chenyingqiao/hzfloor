# coding: utf-8 
from datetime import datetime
import json
import re

from bs4 import BeautifulSoup
import requests

def sendRobot(content):
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=c97d5b18-7d37-4998-a882-5d8ef63f11e9'
    data = {
                        "msgtype":"text",
                        "text":{
                            "content": content
                        }
                    }
    headers = {'Content-Type':'application/json'}
    requests.post(url=url,headers=headers,data=json.dumps(data))

def xslpAllLink():
    allLinks = []
    url = 'https://www.dywfdcxy.cn/website/xslp.jsp'
    # 获取页面数量
    page = requests.post(url)
    searchObj = re.findall(r'共(\d+)页',page.text, re.S)
    if searchObj:
        totelPageNumber = searchObj[0]
        print("开始解析现售楼盘列表......\n")
        print("共{0}页\n".format(totelPageNumber))
        for pageNumber in range(1,int(totelPageNumber)):
            print("解析第{0}页\n".format(pageNumber))
            page = requests.post(url,{
                                    "pageno":pageNumber,
                                    "projectname": "",
                                    'compname': "",
                                    'address': ""
                                })
            soup = BeautifulSoup(page.text,"html.parser")
            # 找到所有链接
            links = soup.find_all('a')
            for link in links:
                # 打印链接的文本和链接
                if "realestate" in link['href']:
                    allLinks.append("https://www.dywfdcxy.cn/website/{0}".format(link["href"]))
    return allLinks

def getProjectPageInfomation(text):
    soup = BeautifulSoup(text,"html.parser")
    tableRow = soup.find_all("tr")
    project_name = ""
    floor = ""
    floor_number = ""
    room_number = ""
    detail_url = ""
    for tableRowItem in tableRow:
        if tableRowItem.find("th") and "项目名称" in tableRowItem.find("th").text:
            project_name = tableRowItem.find("td").text
            print("获取项目信息：{0}".format(project_name))
        if tableRowItem.has_attr("class") and len(tableRowItem["class"]) >0 and tableRowItem["class"][0] == "Searchboxx":
            searchboxxRow = tableRowItem.find_all("td")
            floor = searchboxxRow[0].text
            floor_number = searchboxxRow[3].text
            room_number = searchboxxRow[2].text
            if tableRowItem.find("a"):
                nextPage = tableRowItem.find("a")
                detail_url = "https://www.dywfdcxy.cn/website/{0}".format(nextPage["href"])
    return {
        "project_name": project_name,
        "floor": floor,
        "floor_number": floor_number,
        "room_number": room_number,
        "detail_url": detail_url,
    }

def getALLProjectInfomationAddSaveToDisk(urls):
    data = []
    print("开始解析楼盘详情页.....\n")
    for url in urls:
        page = requests.get(url)
        projectInfomation = getProjectPageInfomation(page.text)
        data.append(projectInfomation)
        break
    return data

def getXiaokong(text):
    print("开始获取销控")
    result = []
    data = {}
    soup = BeautifulSoup(text,"html.parser")
    allTd = soup.find_all("td",{"width":"180"})
    for td in allTd:
        print(td.text)
        if not td.find_all("font",{"class":"house_no"}):
            continue
        houseon = td.find("font",{"class":"house_no"})
        state = td.find("img")["state"]
        houseID = td.find("img")["houseid"]
        stateTrans = {
            "ybz": "已办证",
            "bks": "不可售",
            "cq1": "草签",
            "cq2": "草签",
            "ks": "可售",
        } 
        data["title"] = houseon.text
        if state in stateTrans:
            data["state"] = stateTrans[state]
        else:
            data['state'] = "未知状态"
        data["houseID"] = houseID
        result.append(data)
    return result

def getAllXiaokong(projectData):
    data = []
    for item in range(len(projectData)):
        page = requests.get(projectData[item]["detail_url"])
        projectData[item]["xiaokong"]=getXiaokong(page.text)
    current_datatime = datetime.now()
    f = open("./project-{0}{1}{2}.json".format(current_datatime.year,current_datatime.month,current_datatime.day),'w+')
    f.write(json.dumps(data,ensure_ascii=False))
    f.close()
    return data



def readFile(path):
    f = open(path)
    content = f.read()
    f.close()
    return content


getAllXiaokong(
    getALLProjectInfomationAddSaveToDisk(
        xslpAllLink()
    )
)
#sendRobot("\n".join(str(x) for x in allLinks))
