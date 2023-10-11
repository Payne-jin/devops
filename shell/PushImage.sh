#!/bin/bash
HarBorImage="registry.17dengji.com/kaipanyi-nonlocalsaas/"
AliYunImage="registry.cn-hangzhou.aliyuncs.com/kaipanyi/"

read -ep "请输入需要推送的镜像版本号,如 v5.9.6 ,:" version
#定义需要推送的服务数组
Services=("clientapi" "helper" "jobexecutor" "managerapi" "shh")
# 创建一个空数组来保存用户选择的服务名
Selected_Services=()

#定义镜像推送函数
Push(){
    UpdateImage="$HarBorImage$1:$2"

    echo -e "\033[40;33m 准备拉取镜像: $UpdateImage \033[0m"
    docker pull $UpdateImage
    #获取拉取的镜像ID
    ImageId=`docker images -q $UpdateImage`
    echo -e "\033[40;33m [$UpdateImage]拉取完成后的镜像ID: $ImageId \033[0m" 

    #echo "新镜像地址: $AliYunImage$name:$version
    echo -e "\033[40;33m 新镜像地址: $AliYunImage$1:$2 \033[0m" 
    #重新打镜像标签
    echo -e "\033[40;33m 镜像标签:docker tag ImageId $AliYunImage$1:$2 \033[0m" 
    docker tag $ImageId $AliYunImage$1:$2

    #登录阿里云镜像库
    echo -e "\033[40;33m 登录阿里云镜像库: registry.cn-hangzhou.aliyuncs.com \033[0m" 
    sudo cat ./pwd.txt |docker login --username 登记宝 -password-stdin registry.cn-hangzhou.aliyuncs.com >/dev/null 2>&1

    #推送镜像
    echo -e "\033[40;33m 推送镜像: $AliYunImage$1:$2 \033[0m" 
    docker push $AliYunImage$1:$2

    #删除构建历史镜像
    echo -e "\033[40;33m 删除构建历史镜像 \033[0m" 
#    docker rmi -f $ImageId   
}


# 提示用户选择要推送的服务，允许多选
echo "可选的服务列表:"
for ((i=0; i<${#Services[@]}; i++)); do
  echo "$((i+1)): ${Services[i]}"
done

echo "输入需要推送服务的编号，以逗号分隔 (例如: 1,2,3)，然后按回车"
read -ep "或者输入 'q' 退出: " input

# 检查用户是否选择退出
if [[ "$input" == "q" ]]; then
  echo "退出脚本"
  exit 0
fi

# 解析用户选择的服务
IFS=',' read -ra selected_indices <<< "$input"
for index in "${selected_indices[@]}"; do
  if [[ "$index" -ge 1 && "$index" -le ${#Services[@]} ]]; then
    Selected_Services="${Services[index-1]}"
    Selected_Services+=("$Selected_Services")
  else
    echo "无效的服务编号: $index"
  fi
done


# 并发推送选定的服务
if [[ ${#Selected_Services[@]} -eq 0 ]]; then
	echo "未选择任何服务，退出脚本"
else
	echo "开始并发推送选定的服务..."
	for ss in "${Selected_Services[@]}"; do
		Push $ss $version  
	done
	wait # 等待所有服务推送完成
	echo "所有选定的服务推送完成"
fi



      
