#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#auther: payne-jin

import jenkins
import configparser
import xml.etree.ElementTree as ET

def connect_to_jenkins(jenkins_url, username, api_token):
    return jenkins.Jenkins(jenkins_url, username=username, password=api_token)

def create_view(server, view_name):
    try:
        server.create_view(view_name, jenkins.EMPTY_VIEW_CONFIG_XML)
        print('创建新视图: {}'.format(view_name))
    except jenkins.JenkinsException as e:
        print('创建视图失败: {}'.format(str(e)))

def modify_and_create_project(server, existing_project_name, new_project_name, description, git_repository):
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

        # 将修改后的XML内容转换为字符串
        modified_xml = ET.tostring(root, encoding='unicode')

        # 将修改后的配置文件内容保存为XML文件
        with open('modified_project_config.xml', 'w', encoding='utf-8') as modified_xml_file:
            modified_xml_file.write(modified_xml)

        print('修改后的项目配置文件已保存为 modified_project_config.xml')

        # 创建新项目
        server.create_job(new_project_name, modified_xml)
        print('创建新项目: {}'.format(new_project_name))

    except jenkins.JenkinsException as e:
        print('操作失败: {}'.format(str(e)))
    except Exception as e:
        print('操作失败: {}'.format(str(e)))

def add_project_to_view(server, view_name, new_project_name):
    try:
        view_config = server.get_view_config(view_name)
        view_root = ET.fromstring(view_config)

        new_project = ET.Element('string')
        new_project.text = new_project_name

        projects_element = view_root.find('.//jobNames')
        projects_element.append(new_project)

        new_view_config = ET.tostring(view_root, encoding='unicode')

        server.reconfig_view(view_name, new_view_config)
        print('新项目: {} 已添加到新视图: {}'.format(new_project_name, view_name))

    except jenkins.JenkinsException as e:
        print('操作失败: {}'.format(str(e)))
    except Exception as e:
        print('操作失败: {}'.format(str(e)))

if __name__ == "__main__":
    # 读取配置文件
    config = configparser.ConfigParser()
    config.read('jenkins_job_config.ini')

    # 从配置文件中获取Jenkins和项目的信息
    jenkins_url = config['JenkinsConfig']['jenkins_url']
    username = config['JenkinsConfig']['username']
    api_token = config['JenkinsConfig']['api_token']
    view_name = config['ProjectConfig']['view_name']
    existing_project_name = 'bbc-api'  # 已存在的项目名称
    new_project_name = config['ProjectConfig']['project_name']
    description = config['ProjectConfig']['job_description']
    git_repository = config['ProjectConfig']['git_repository']

    server = connect_to_jenkins(jenkins_url, username, api_token)
    create_view(server, view_name)
    modify_and_create_project(server, existing_project_name, new_project_name, description, git_repository)
    add_project_to_view(server, view_name, new_project_name)
