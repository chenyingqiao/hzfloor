# coding: utf-8
from codecs import decode
from datetime import datetime
import json
import os
import re
import sys

from bs4 import BeautifulSoup
import requests


def sendRobot(content):
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=c97d5b18-7d37-4998-a882-5d8ef63f11e9'
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    headers = {'Content-Type': 'application/json'}
    requests.post(url=url, headers=headers, data=json.dumps(data))


def xslpAllLink():
    allLinks = []
    url = 'https://www.dywfdcxy.cn/website/xslp.jsp'
    # 获取页面数量
    page = requests.post(url)
    searchObj = re.findall(r'共(\d+)页', page.text, re.S)
    if searchObj:
        totelPageNumber = searchObj[0]
        print("开始解析现售楼盘列表......\n")
        print("共{0}页\n".format(totelPageNumber))
        # totelPageNumber = 2
        for pageNumber in range(1, int(totelPageNumber)):
            print("解析第{0}页\n".format(pageNumber))
            page = requests.post(url, {
                "pageno": pageNumber,
                "projectname": "",
                'compname': "",
                'address': ""
            })
            soup = BeautifulSoup(page.text, "html.parser")
            # 找到所有链接
            links = soup.find_all('a')
            reshow = {}
            for link in links:
                if link["href"] in reshow.keys():
                    continue
                reshow[link["href"]] = True
                # 打印链接的文本和链接
                if "realestate" in link['href']:
                    allLinks.append(
                        "https://www.dywfdcxy.cn/website/{0}".format(link["href"]))
    return allLinks


def getProjectPageInfomation(text):
    soup = BeautifulSoup(text, "html.parser")
    tableRow = soup.find_all("tr")
    project_name = ""
    floor = ""
    floor_number = ""
    room_number = ""
    detail_url = ""

    data = []
    for tableRowItem in tableRow:
        if tableRowItem.find("tr"):
            continue
        if tableRowItem.find("th") and "项目名称" in tableRowItem.find("th").text:
            project_name = tableRowItem.find("td").text
            print("获取项目信息：{0}".format(project_name))
        if tableRowItem.has_attr("class") and len(tableRowItem["class"]) > 0 and tableRowItem["class"][0] == "Searchboxx":
            searchboxxRow = tableRowItem.find_all("td")
            floor = searchboxxRow[0].text
            floor_number = searchboxxRow[3].text
            room_number = searchboxxRow[2].text
            if tableRowItem.find("a"):
                nextPage = tableRowItem.find("a")
                detail_url = "https://www.dywfdcxy.cn/website/{0}".format(
                    nextPage["href"])
            data.append({
                "project_name": project_name,
                "floor": floor,
                "floor_number": floor_number,
                "room_number": room_number,
                "detail_url": detail_url,
            })
    return data


def getALLProjectInfomationAddSaveToDisk(urls):
    data = []
    print("开始解析楼盘详情页.....\n")
    for url in urls:
        page = requests.get(url)
        projectInfomation = getProjectPageInfomation(page.text)
        data = data + projectInfomation
    return data


def getXiaokong(text):
    print("开始获取销控")
    result = []
    soup = BeautifulSoup(text, "html.parser")
    allTd = soup.find_all("td", {"width": "180"})
    for td in allTd:
        if not td.find_all("font", {"class": "house_no"}):
            continue
        data = {}
        houseon = td.find("font", {"class": "house_no"})
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

def isRightRoomInfomation(houseID):
    print("请求面积数据{}\n".format(houseID))
    url = "https://www.dywfdcxy.cn/website/house.jsp?id={0}&lcStr=0".format(houseID)
    try:
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        allTh = soup.find_all("th",{"align":"right"})
        for th in allTh:
            if "实测面积" in th.text:
                area = th.parent.find_all("td")
                if len(area) != 2:
                    continue
                if float(area[1].text.strip()) > 85.1 and float(area[1].text.strip()) < 150.1:
                    return True
        return False
    except:
        print("请求{}错误".format(url))
        return True

def getAllXiaokongToDisk(projectData):
    for item in range(len(projectData)):
        try:
            page = requests.get(projectData[item]["detail_url"])
            projectData[item]["xiaokong"] = getXiaokong(page.text)
        except:
            continue
    return projectData


def writeFile(path, content):
    f = open(path, "w+")
    f.write(content)
    f.close()


def readFile(path):
    f = open(path, "+w")
    content = f.read()
    f.close()
    return content


def collectionData(data):
    current_datatime = datetime.now()
    todayPath = "./project-{0}{1}{2}.json".format(current_datatime.year,
                                                  current_datatime.month, current_datatime.day)
    yestodayPath = ""
    content = ""
    sendRobot("=今日{0}年{1}月{2}日楼盘数据=\n".format(current_datatime.year,
                                                  current_datatime.month, current_datatime.day))
    projectCollection = {}
    for item in data:
        for xk in item["xiaokong"]:
            ckey = "{0}".format(item["project_name"])
            if ckey not in projectCollection:
                projectCollection[ckey] = {}
            if item["floor"] not in projectCollection[ckey]:
                projectCollection[ckey][item["floor"]] = {
                    "number": 0,
                    "url": "",
                }
            if xk["state"] == "可售":
                # 读取并比对现在的数据
                projectCollection[ckey][item["floor"]]["number"] += 1
                projectCollection[ckey][item["floor"]]["url"] = item["detail_url"]
                projectCollection[ckey][item["floor"]]["houseID"] = xk["houseID"]
    [(k, projectCollection[k]) for k in sorted(projectCollection.keys())]
    for key in projectCollection.keys():
        content += "# {0}\n".format(key)
        for fkey in projectCollection[key].keys():
            item = projectCollection[key][fkey]
            if item["number"] == 0:
                continue
            if not isRightRoomInfomation(item["houseID"]):
                continue
            content += "[{0}]({1}) 剩下{2}间房\n".format(fkey,item["url"], item["number"])
            if sys.getsizeof(content) >= 3500:
                content = "今日{0}年{1}月{2}日楼盘数据\n".format(current_datatime.year,
                                                        current_datatime.month, current_datatime.day) + content
                sendRobot(content=content)
                content = ""
    if content != "":
        content = "今日{0}年{1}月{2}日楼盘数据\n".format(current_datatime.year,
                                                current_datatime.month, current_datatime.day) + content
        sendRobot(content=content)
    if os.path.exists(yestodayPath):
        yestodayData = json.loads(readFile(yestodayPath))
    # 写入今天的数据
    writeFile(todayPath, json.dumps(data, ensure_ascii=False))
    return


data = getAllXiaokongToDisk(
    getALLProjectInfomationAddSaveToDisk(
        xslpAllLink()
    )
)
collectionData(data)
# sendRobot("\n".join(str(x) for x in allLinks))
