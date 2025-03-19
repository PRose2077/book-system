// 文件开始加载时立即输出
console.log('=== upload.js 开始加载 ===');

// 检查依赖项
if (typeof jQuery === 'undefined') {
    console.error('jQuery 未加载');
} else {
    console.log('jQuery 已加载');
}

if (typeof layui === 'undefined') {
    console.error('layui 未加载');
} else {
    console.log('layui 已加载');
}

// 全局函数定义
window.loadSessionUploads = function() {
    var history = JSON.parse(sessionStorage.getItem('uploadHistory') || '[]');
    if (history.length === 0) {
        window.updateUploadTable([]);
        return;
    }
    
    $.ajax({
        url: '/api/upload/session-history',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ file_ids: history }),
        success: function(res) {
            if (res.code === 0) {
                window.updateUploadTable(res.data);
            } else {
                layer.msg('获取上传历史失败');
            }
        },
        error: function() {
            layer.msg('获取上传历史失败');
        }
    });
};


window.updateUploadTable = function(uploads) {
    var html = '';
    if (uploads && uploads.length > 0) {
        uploads.forEach(function(upload) {
            // 状态显示逻辑
            let statusHtml = '';
            let statusClass = '';
            
            switch(upload.status) {
                case 'queued':
                    statusClass = 'status-badge status-pending';
                    statusHtml = `排队中 (${upload.queue_position-1})`;
                    break;
                case 'processing':
                    statusClass = 'status-badge status-processing';
                    statusHtml = '处理中';
                    break;
                case 'completed':
                    statusClass = 'status-badge status-completed';
                    statusHtml = '已完成';
                    break;
                case 'failed':
                    statusClass = 'status-badge status-failed';
                    statusHtml = '失败';
                    break;
                default:
                    statusClass = 'status-badge';
                    statusHtml = upload.status;
            }
            
            // 添加操作按钮
            let operationHtml = `
                <button class="layui-btn layui-btn-xs" onclick="viewDetails('${upload.file_id}')">
                    <i class="layui-icon layui-icon-search"></i> 查看详情
                </button>
                <button class="layui-btn layui-btn-xs layui-btn-danger" onclick="deleteUpload('${upload.file_id}')">
                    <i class="layui-icon layui-icon-delete"></i> 删除
                </button>
            `;
            
            html += `
                <tr>
                    <td>${upload.filename}</td>
                    <td>${upload.size}</td>
                    <td><span class="${statusClass}">${statusHtml}</span></td>
                    <td>${upload.upload_time}</td>
                    <td>${upload.last_updated}</td>
                    <td>${upload.total_records || 0}</td>
                    <td>${upload.error_message || '-'}</td>
                    <td>${operationHtml}</td>
                </tr>
            `;
        });
    } else {
        html = '<tr><td colspan="8" style="text-align: center;">暂无上传记录</td></tr>';
    }
    $('#uploadHistory tbody').html(html);
};

// 查看详情和删除功能
window.viewDetails = function(fileId) {
    window.location.href = `/upload/details/${fileId}`;
};

window.deleteUpload = function(fileId) {
    layer.confirm('确定要删除这个文件吗？这将同时删除相关的书籍和评论数据。', {
        btn: ['确定','取消']
    }, function(){
        $.ajax({
            url: `/api/upload/${fileId}`,
            type: 'DELETE',
            success: function(res) {
                if(res.code === 0) {
                    layer.msg(`删除成功，共删除${res.data.deleted_books}本书的数据`);
                    window.loadSessionUploads();  // 刷新列表
                } else {
                    layer.msg(res.msg);
                }
            },
            error: function() {
                layer.msg('删除失败，请重试');
            }
        });
    });
};

// 标签相关的全局函数
window.addGlobalTag = function(tag) {
    if (!window.globalTags) {
        window.globalTags = new Set();
    }
    if (!window.globalTags.has(tag)) {
        window.globalTags.add(tag);
        window.updateSelectedTagsDisplay();
        window.saveTagsToStorage();
    }
};

window.updateSelectedTagsDisplay = function() {
    const container = $('#selectedTags');
    container.empty();
    
    window.globalTags.forEach(tag => {
        const tagElement = $('<span class="selected-tag"></span>')
            .text(tag)
            .append('<span class="close-btn">×</span>');
        
        tagElement.find('.close-btn').click(function() {
            window.globalTags.delete(tag);
            window.updateSelectedTagsDisplay();
            window.saveTagsToStorage();
        });
        
        container.append(tagElement);
    });
};

window.saveTagsToStorage = function() {
    const data = {
        tags: Array.from(window.globalTags),
        timestamp: new Date().getTime()
    };
    localStorage.setItem('selectedTagsData', JSON.stringify(data));
};

// 验证文件名是否包含中文
function hasChineseChar(str) {
    return /[\u4e00-\u9fa5]/.test(str);
}

function validateCSVFormat(file) {
    return new Promise((resolve, reject) => {
        // 首先检查文件名
        if (hasChineseChar(file.name)) {
            reject('文件名不能包含中文字符');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const firstLine = e.target.result.split('\n')[0].trim();
            const headers = firstLine.split(',').map(h => h.trim());
            
            // 必需的列
            const requiredHeaders = ['book_id', 'book_title', 'comment_id', 'content'];
            
            // 检查必需的列是否都存在
            const missingRequired = requiredHeaders.filter(h => !headers.includes(h));
            
            if (missingRequired.length > 0) {
                reject(`CSV文件缺少必需的列：${missingRequired.join(', ')}`);
            } else {
                resolve(true);
            }
        };
        reader.onerror = function() {
            reject('读取文件失败');
        };
        reader.readAsText(file);
    });
}

// 主要初始化逻辑
$(document).ready(function() {
    console.log('页面加载完成，开始初始化');
    
    // Layui 模块加载
    layui.use(['upload', 'layer'], function(){
        var upload = layui.upload;
        var layer = layui.layer;
        let uploadHistoryTimer = null;  // 定时器变量
        
        // 初始化会话上传历史
        if (!sessionStorage.getItem('uploadHistory')) {
            sessionStorage.setItem('uploadHistory', JSON.stringify([]));
        }
        
        // 上传组件初始化
        var uploadInst = upload.render({
            elem: '#uploadArea',
            url: '/api/upload',
            accept: 'file',
            exts: 'csv',
            drag: true,         
            multiple: false,    // 不允许多文件
            auto: false,        // 不自动上传
            choose: function(obj) {
                // 获取当前选择的文件
                obj.preview(async function(index, file) {
                    try {
                        // 验证文件格式
                        await validateCSVFormat(file);
                        // 验证通过，开始上传
                        layer.load();
                        obj.upload(index, file);
                    } catch (error) {
                        layer.msg(error);
                        // 移除无效文件
                        delete obj.pushFile()[index];
                    }
                });
            },
            done: function(res){
                layer.closeAll('loading');
                if(res.code === 0){
                    var history = JSON.parse(sessionStorage.getItem('uploadHistory') || '[]');
                    history.push(res.file_id);
                    sessionStorage.setItem('uploadHistory', JSON.stringify(history));
                    layer.msg('文件上传成功，开始处理');
                    window.loadSessionUploads();  // 立即加载一次
                    startUploadHistoryCheck();    // 启动轮询
                } else {
                    layer.msg(res.msg || '上传失败');
                }
            },
            error: function(){
                layer.closeAll('loading');
                layer.msg('上传失败，请重试');
            }
        });
        
        // 初始化拖拽上传区域样式
        var uploadArea = $('.upload-area')[0];
        if (uploadArea) {
            uploadArea.addEventListener('dragover', function(e) {
                e.preventDefault();
                $(this).addClass('dragover');
            });

            uploadArea.addEventListener('dragleave', function(e) {
                e.preventDefault();
                $(this).removeClass('dragover');
            });

            uploadArea.addEventListener('drop', function(e) {
                e.preventDefault();
                $(this).removeClass('dragover');
            });
        } 
        
        // 初始化事件监听
        $('.layui-btn-refresh').on('click', function() {
            window.loadSessionUploads();
            layer.msg('已刷新上传历史');
        });

        $('#addCustomTag').click(function(e) {
            e.stopPropagation();
            $('.custom-tag-input-group').toggle();
            if($('.custom-tag-input-group').is(':visible')) {
                $('#customTagInput').focus();
            }
        });

        $('.add-custom-tag-btn').click(function() {
            var tag = $('#customTagInput').val().trim();
            if(tag) {
                window.addGlobalTag(tag);
                $('#customTagInput').val('');
                $('.custom-tag-input-group').hide();
            }
        });

        $('#customTagInput').keypress(function(e) {
            if(e.which == 13) {
                $('.add-custom-tag-btn').click();
            }
        });

        $(document).on('click', '.draggable-tag', function() {
            var tag = $(this).data('tag') || $(this).text().trim();
            window.addGlobalTag(tag);
            layer.msg('已添加标签：' + tag);
        });

        $(document).click(function(e) {
            if(!$(e.target).closest('.custom-tag-input-group, #addCustomTag').length) {
                $('.custom-tag-input-group').hide();
            }
        });

        // 上传历史检查函数
        function startUploadHistoryCheck() {
            // 清除之前的定时器
            if (uploadHistoryTimer) {
                clearInterval(uploadHistoryTimer);
            }
            
            // 只有当有上传历史时才开始轮询
            var history = JSON.parse(sessionStorage.getItem('uploadHistory') || '[]');
            if (history.length > 0) {
                uploadHistoryTimer = setInterval(function() {
                    $.ajax({
                        url: '/api/upload/session-history',
                        type: 'POST',
                        contentType: 'application/json',
                        data: JSON.stringify({ file_ids: history }),
                        success: function(res) {
                            if (res.code === 0) {
                                window.updateUploadTable(res.data);
                                // 如果所有任务都完成了，停止轮询
                                if (res.data.every(item => 
                                    item.status === 'completed' || 
                                    item.status === 'failed'
                                )) {
                                    clearInterval(uploadHistoryTimer);
                                    uploadHistoryTimer = null;
                                }
                            }
                        }
                    });
                }, 30000);  // 30秒检查一次
            }
        }
        
        // 初始加载上传历史并启动检查
        window.loadSessionUploads();
        startUploadHistoryCheck();
    });
});