#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author: payne-jin
'''
该脚本主要针对新项目上线，自动化配置Jenkins job并触发job构建.新项目的名称和仓库地址等参数需要在配置文件jenkins_job_config.ini 手动定义，请先根据自己的Jenkins项目模板先修改该变量的值 existing_project_name = 'template'  
Jenkins 新建项目  
1.创建Jenkins视图
2.创建Jenkins自由风格的软件项目
3.调用gitlab api  配置项目的webhook
4.触发job构建，并通过Jenkins任务中的shell脚本(build.sh)创建新项目的harbar仓库和创建k8s服务并发布

'''

import jenkins
import configparser
import xml.etree.ElementTree as ET
import requests

def connect_to_jenkins(jenkins_url, username, api_token):
    return jenkins.Jenkins(jenkins_url, username=username, password=api_token)

def create_view(server, view_name):
    try:
        server.create_view(view_name, jenkins.EMPTY_VIEW_CONFIG_XML)
        print('创建新视图: {}'.format(view_name))
    except jenkins.JenkinsException as e:
        print('创建视图失败: {}'.format(str(e)))

def modify_and_create_project(server, existing_project_name, new_project_name, description, git_repository, build_branch):
    try:
        config_xml = server.get_job_config(existing_project_name)
        root = ET.fromstring(config_xml)
        # 修改项目描述
        description_element = root.find('.//description')
        description_element.text = description
        # 修改Git仓库地址
        git_url_element = root.find('.//scm/userRemoteConfigs/hudson.plugins.git.UserRemoteConfig/url')
        git_url_element.text = git_repository
        # 修改webhook token
        webhook_token_element = root.find('.//token')
        webhook_token_element.text = new_project_name
        #修改scm 分支名
        scm_branch_name_element = root.find('.//scm/branches/hudson.plugins.git.BranchSpec/name')
        scm_branch_name_element.text = build_branch
        # 将修改后的XML内容转换为字符串
        modified_xml = ET.tostring(root, encoding='unicode')
        # 将修改后的配置文件内容保存为XML文件
        with open('modified_project_config.xml', 'w', encoding='utf-8') as modified_xml_file:
            modified_xml_file.write(modified_xml)
        print('修改后的项目配置文件已保存为 modified_project_config.xml')
        # 创建新项目
        server.create_job(new_project_name, modified_xml)
        print('创建新项目: {}'.format(new_project_name))
	#获取远程触发构建的token
        remote_token_element = root.find('.//authToken')
        remote_token = remote_token_element.text  # 获取remote_token的值
        return remote_token # 将remote_token作为函数的返回值返回
    except jenkins.JenkinsException as e:
        print('操作失败: {}'.format(str(e)))
    except Exception as e:
        print('操作失败: {}'.format(str(e)))

def add_project_to_view(server, view_name, new_project_name, remote_token, build_parameters):
    try:
        view_config = server.get_view_config(view_name)
        view_root = ET.fromstring(view_config)
        new_project = ET.Element('string')
        new_project.text = new_project_name
        projects_element = view_root.find('.//jobNames')
        projects_element.append(new_project)
        new_view_config = ET.tostring(view_root, encoding='unicode')
        server.reconfig_view(view_name, new_view_config)
        print('新项目: {} 已添加到视图: {}'.format(new_project_name, view_name))
        #触发构建任务
        server.build_job(new_project_name, parameters=build_parameters, token=remote_token)
        print(f'已触发Jenkins项目 {new_project_name} 的构建.')	
    except jenkins.JenkinsException as e:
        print(f'触发Jenkins构建失败: {str(e)}')
    except Exception as e:
        print('操作失败: {}'.format(str(e)))

def get_project_id_by_name(gitlab_url, private_token, repository_name):
    params = {'search': repository_name}
    response = requests.get(gitlab_url, headers=headers, params=params)
    if response.status_code == 200:
        projects = response.json()
        for project in projects:
            if project["name"] == repository_name:
                return project["id"]
    else:
        print(f"Failed to retrieve project list: {response.status_code}")
    return None

def webhook_exists(webhooks, target_url):
    for webhook in webhooks:
        if webhook["url"] == target_url:
            return True
    return False

def add_webhook_to_gitlab(webhook_url, git_repository, gitlab_url, private_token):
    try:
        repository_name = git_repository.split("/")[-1].replace(".git", "")
        repository_id = get_project_id_by_name(gitlab_url, private_token, repository_name)
        if repository_id:
            gitlab_api_url = f'{gitlab_url}/{repository_id}/hooks'
            data = {'url': webhook_url, 'merge_requests_events': True, 'push_events': True}
            response = requests.get(gitlab_api_url, headers=headers)
            response.raise_for_status()  # 如果请求失败，将引发HTTPError异常
            existing_webhooks = response.json()
            if not webhook_exists(existing_webhooks, webhook_url):
                response = requests.post(gitlab_api_url, headers=headers, data=data)
                response.raise_for_status()  # 如果请求失败，将引发HTTPError异常
                print('Webhook 已成功添加到 GitLab 项目.')
            else:
                print('Webhook 已存在，不需要再次添加.')
        else:
            print(f'无法找到与仓库名称"{repository_name}"匹配的项目.')
    except requests.exceptions.HTTPError as errh:
        print(f'HTTP错误发生: {errh}')
    except requests.exceptions.ConnectionError as errc:
        print(f'错误的连接: {errc}')
    except requests.exceptions.Timeout as errt:
        print(f'请求超时: {errt}')
    except requests.exceptions.RequestException as err:
        print(f'发生异常错误: {err}')

if __name__ == "__main__":
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('jenkins_job_config.ini')
    # 从配置文件中获取Jenkins和项目的信息
    jenkins_url = config['JenkinsConfig']['jenkins_url']
    username = config['JenkinsConfig']['username']
    api_token = config['JenkinsConfig']['api_token']
    view_name = config['ProjectConfig']['view_name']
    existing_project_name = 'template'  # 已存在的项目名称,需要根据自己的模板项目进行修改
    new_project_name = config['ProjectConfig']['project_name']
    description = config['ProjectConfig']['job_description']
    git_repository = config['ProjectConfig']['git_repository']
    generic_webhook_url = f'{jenkins_url}/generic-webhook-trigger/invoke?token={new_project_name}'
    headers = {'PRIVATE-TOKEN': config['GitlabConfig']['PRIVATE-TOKEN']}
    gitlab_url = config['GitlabConfig']['gitlab_url']
    git_credentialsId = config['ProjectConfig']['credentialsId']
    build_branch = config['ProjectConfig']['build_branch']
    build_parameters = {'BRANCH': config['ProjectConfig']['build_branch']}
    server = connect_to_jenkins(jenkins_url, username, api_token)
    create_view(server, view_name)
    remote_token = modify_and_create_project(server, existing_project_name, new_project_name, description, git_repository, build_branch)
    add_project_to_view(server, view_name, new_project_name, remote_token, build_parameters)
    if generic_webhook_url:
        print('Generic Webhook Trigger URL: {}'.format(generic_webhook_url))
        # 将Generic Webhook Trigger的URL添加到GitLab项目的Webhook中
        add_webhook_to_gitlab(generic_webhook_url, git_repository, gitlab_url, headers)
    else:
        print('获取Generic Webhook Trigger URL失败，无法添加到GitLab Webhook.')

