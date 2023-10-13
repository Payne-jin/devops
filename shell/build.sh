#!/bin/bash
#auther: payne-jin

export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1
#获取当前执行项目的视图名,注意：创建新项目时，请确保Jenkins中的视图名和git仓库名保持一致
VIEW_NAME=$(basename "${GIT_URL}" .git)
echo "####获取当前项目所在的视图名: ${VIEW_NAME}####"
#Dev_namespace="${JOB_NAME}"
Qa_namespace="test-${VIEW_NAME}"
Pod_name="${JOB_NAME}"
#Repostitory_name="${JOB_NAME}"
#Tag_name="${JOB_NAME}"
#获取新项目仓库地址
Project_Harbor="$(curl -u "admin:`cat /data/script/ops/password_config.txt | openssl enc -d -aes-256-cbc -a -salt -pass pass:123456`" -X GET -H "Content-Type: application/json" https://registry.17dengji.com/api/v2.0/projects?name=${VIEW_NAME} -s)"
echo "仓库名: ${Project_Harbor}"
#GIT_PATH="Dengjibao/Dengjibao.Web/Dengjibao.Web.csproj"
#GIT_PATH="Miniprogam/Djb.Api/Djb.Api.csproj"

echo "分支：$GIT_BRANCH"
#定义获取镜像名函数
DefinImageName(){
	mkdir $WORKSPACE/jenkins_publish
	if [ ! -n "${ref}" ];then
		branch_name=`echo  ${GIT_BRANCH} | awk -F '/' '{print $NF}'`
		IMAGE_NAME="registry.17dengji.com/$VIEW_NAME/$Pod_name:$branch_name"
        echo ${IMAGE_NAME}
	else
		branch_name=`echo  ${ref} | awk -F '/' '{print $NF}'`
        IMAGE_NAME="registry.17dengji.com/$VIEW_NAME/$Pod_name:$branch_name"
		echo ${IMAGE_NAME}
	fi
}

echo '####查看打包环境####'
which dotnet
dotnet --info
dotnet --version

echo '####获取镜像名####'
if [ -d "$WORKSPACE/jenkins_publish" ];then
	rm -rf $WORKSPACE/jenkins_publish && DefinImageName
else
	DefinImageName
fi

#从dockerfile中获取需要运行的模块名
ModuleName=$(tail -n 1 `find $WORKSPACE -type d -name "bin" -prune -o -type f -iname "Dockerfile" -print|head -n 1`|awk -F',' '{ print $NF }'|awk 'BEGIN{FS=OFS="."}{NF--;}{print}'|sed 's/^"//')

#获取模块工程文件
CountCsproj=$(find $WORKSPACE -name *.csproj -type f  -printf "%P\n" |grep $ModuleName|wc -l)
if [ ${CountCsproj} -eq 1 ];then
	Csproj=$(find $WORKSPACE -name *.csproj -type f  -printf "%P\n" |grep $ModuleName)
	echo "获取模块工程文件 ${Csproj}"
else
	echo "####获取模块工程文件出错，请检查从dockerfile中获取需要运行的模块名是否正确####"
	exit 1
fi
echo '####编译.NET程序####'
#dotnet nuget add source http://192.168.3.167:16666/repository/nuget-hosted
dotnet publish $WORKSPACE/${Csproj}  -c:Release -f netcoreapp3.1 -o $WORKSPACE/jenkins_publish

echo '####构建镜像####'
if [ ! -f $WORKSPACE/jenkins_publish/Dockerfile ];then
        echo "####Dockerfile 不存在####"
        exit 1
else
	cd $WORKSPACE/jenkins_publish
	docker build -t  ${IMAGE_NAME} .
	if [ $? -eq 0 ];then
		echo "####镜像构建成功，开始推送镜像####"
		if [ "$Project_Harbor" = "[]" ];then
			echo "####项目私有仓库不存在，执行仓库创建####"
			curl -u "admin:`cat /data/script/ops/password_config.txt | openssl enc -d -aes-256-cbc -a -salt -pass pass:123456`" -X POST -H "Content-Type: application/json" "https://registry.17dengji.com/api/v2.0/projects" -d "{\"project_name\":
			\"${VIEW_NAME}\", \"metadata\": {\"public\": \"true\"}, \"storage_limit\": -1}" > /dev/null 2>&1 
			echo "####私有仓库创建成功，开始推送镜像中####"
			docker push $IMAGE_NAME
		else
			echo "####私有项目仓库已经存在，开始推送镜像中####"
			docker push $IMAGE_NAME
		fi
		echo '####删除镜像####'
		docker rmi -f $IMAGE_NAME
	else
		echo "####镜像构建失败####"
		exit 1
	fi
fi

# 定义更新pod函数
Update_Pod(){
	echo '####更新pod####'
#	if [[ "$branch_name" =~ "dev" ]];then
#		kubectl set image deployment -n $Dev_namespace $Pod_name   $Pod_name=$IMAGE_NAME --kubeconfig  /root/.kube/config
#		if [ $? -eq 0 ];then
#        		echo "Image not updated"
#        		kubectl rollout  restart deployment  -n  $Dev_namespace $Pod_name --kubeconfig  /root/.kube/config
#		fi
#	elif [[ "$branch_name" =~ "test" ]];then 
		kubectl set image deployment -n $Qa_namespace $Pod_name   $Pod_name=$IMAGE_NAME --kubeconfig  /root/.kube/config
		if [ $? -eq 0 ];then
        	echo "####Image not updated####"
        	kubectl rollout  restart deployment  -n  $Qa_namespace $Pod_name --kubeconfig  /root/.kube/config
		fi
#	else 
#		echo "release分支为生产环境分支，需手动更新"
#	fi
}

#定义创建k8s pod函数
Create_Pod(){
	# 渲染Deployment配置
	jinja2 /data/script/ops/k8s_template_yml/deployment.yaml.j2 -D project_name=$Pod_name -D image_name=$IMAGE_NAME -D view_name=test-${VIEW_NAME} -o deployment.yaml

	# 渲染Service配置
	jinja2 /data/script/ops/k8s_template_yml/service.yaml.j2 -D project_name=$Pod_name -D view_name=test-${VIEW_NAME} -o service.yaml

	# 渲染Ingress配置
	jinja2 /data/script/ops/k8s_template_yml/ingress.yaml.j2 -D project_name=$Pod_name -D view_name=test-${VIEW_NAME} -o ingress.yaml

	# 应用Kubernetes资源配置文件
	kubectl apply -f deployment.yaml
	kubectl apply -f service.yaml
	kubectl apply -f ingress.yaml
	# 等待Pod部署完成
	#kubectl rollout status deployment/${Pod_name}
	echo "####Deployment completed successfully.####"
}


# 根据视图名称，检查对应项目的Kubernetes命名空间是否存在，如果不存在则创建
kubectl get namespace test-${VIEW_NAME} > /dev/null 2>&1
if [ $? -ne 0 ]; then
    kubectl create namespace test-${VIEW_NAME}
    echo "####项目命名空间 test-${VIEW_NAME} created.####"
    Create_Pod
else
    echo "####命名空间已存在，直接更新测试环境服务.####"
    Update_Pod
fi
