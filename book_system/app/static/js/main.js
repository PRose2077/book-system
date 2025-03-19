// 等待文档加载完成
layui.use(['element', 'layer', 'form'], function(){
    var element = layui.element;
    var layer = layui.layer;
    var form = layui.form;
    
    // 初始化通知系统
    window.notificationSystem = {
        // 存储生成状态
        generationStatus: {
            isGenerating: false,
            isCompleted: false,
            content: null,
            notified: false,
            taskId: null  // 添加taskId字段用于存储任务ID
        },
        
        // 初始化方法，从本地存储加载状态
        init: function() {
            // 检查是否已经初始化过，避免重复初始化
            if (this.initialized) {
                console.log('通知系统已经初始化过，跳过');
                return;
            }
            
            // 从本地存储加载状态
            const savedStatus = localStorage.getItem('generationStatus');
            console.log('初始化通知系统，检查本地存储状态:', savedStatus ? '找到保存的状态' : '未找到保存的状态');
            
            if (savedStatus) {
                try {
                    const parsedStatus = JSON.parse(savedStatus);
                    this.generationStatus = {...this.generationStatus, ...parsedStatus};
                    console.log('加载的生成状态:', this.generationStatus);
                    
                    // 检查待处理的生成任务
                    this.checkPendingGenerations();
                    
                    // 如果有完成但未通知的内容，显示通知
                    if (this.generationStatus.isCompleted && !this.generationStatus.notified && this.generationStatus.content) {
                        console.log('检测到未通知的已完成内容，显示通知');
                        this.showGenerationCompleteNotification();
                    }
                } catch (e) {
                    console.error('解析保存的生成状态时出错:', e);
                    localStorage.removeItem('generationStatus');
                }
            }
            
            // 设置定期检查生成状态的定时器
            this.checkIntervalId = setInterval(() => {
                this.checkPendingGenerations();
            }, 30000); // 每30秒检查一次
            
            // 标记为已初始化
            this.initialized = true;
        },
        
        // 显示通知
        showNotification: function(title, message, type, actions) {
            const container = document.getElementById('notificationContainer');
            const notificationId = 'notification-' + Date.now();
            
            // 创建通知元素
            const notification = document.createElement('div');
            notification.className = `notification ${type || ''}`;
            notification.id = notificationId;
            
            // 构建通知内容
            let notificationHTML = `
                <div class="notification-content">
                    <div class="notification-title">${title}</div>
                    <div class="notification-message">${message}</div>
                </div>
            `;
            
            // 添加操作按钮
            if (actions && actions.length) {
                notificationHTML += '<div class="notification-actions">';
                actions.forEach(action => {
                    notificationHTML += `<button class="notification-btn" data-action="${action.action}">${action.text}</button>`;
                });
                notificationHTML += '</div>';
            }
            
            // 添加关闭按钮
            notificationHTML += '<button class="notification-close">×</button>';
            
            notification.innerHTML = notificationHTML;
            container.appendChild(notification);
            
            // 显示通知
            setTimeout(() => {
                notification.classList.add('show');
            }, 10);
            
            // 绑定按钮事件
            if (actions && actions.length) {
                actions.forEach(action => {
                    const button = notification.querySelector(`[data-action="${action.action}"]`);
                    if (button && action.handler) {
                        button.addEventListener('click', () => {
                            action.handler();
                            this.closeNotification(notificationId);
                        });
                    }
                });
            }
            
            // 绑定关闭按钮事件
            const closeBtn = notification.querySelector('.notification-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    this.closeNotification(notificationId);
                });
            }
            
            // 自动关闭（如果设置了）
            if (actions && actions.some(a => a.action === 'view')) {
                // 如果有查看按钮，不自动关闭
            } else {
                // 否则5秒后自动关闭
                setTimeout(() => {
                    this.closeNotification(notificationId);
                }, 5000);
            }
            
            return notificationId;
        },
        
        // 关闭通知
        closeNotification: function(id) {
            const notification = document.getElementById(id);
            if (notification) {
                notification.classList.add('hide');
                setTimeout(() => {
                    notification.remove();
                }, 300);
            }
        },
        
        // 设置生成状态
        setGenerationStatus: function(status) {
            const oldStatus = {...this.generationStatus};
            this.generationStatus = {...this.generationStatus, ...status};
            console.log('生成状态更新:', oldStatus, ' -> ', this.generationStatus);
            
            // 保存状态到本地存储
            localStorage.setItem('generationStatus', JSON.stringify(this.generationStatus));
            
            // 如果生成完成且未通知，显示通知
            if (this.generationStatus.isCompleted && !this.generationStatus.notified && this.generationStatus.content) {
                console.log('内容生成完成，准备显示通知');
                this.showGenerationCompleteNotification();
            }
        },
        
        // 显示生成完成通知
        showGenerationCompleteNotification: function() {
            console.log('显示生成完成通知');
            
            // 标记为已通知
            this.setGenerationStatus({
                notified: true
            });
            
            this.showNotification(
                '内容生成完成', 
                '您的内容已生成完成，点击查看按钮查看结果。',
                'success',
                [
                    {
                        text: '查看',
                        action: 'view',
                        handler: () => {
                            console.log('用户点击查看按钮');
                            
                            // 如果有任务ID，跳转到结果详情页
                            if (this.generationStatus.taskId) {
                                window.location.href = `/generation/result/${this.generationStatus.taskId}`;
                                return;
                            }
                            
                            // 否则使用旧的弹窗方式显示
                            if (this.generationStatus.content) {
                                layer.open({
                                    type: 1,
                                    title: ['写作指导', 'background-color: #37271C; color: #F5E6D3; border-bottom: 1px solid #9F6A38;'],
                                    area: ['800px', '600px'],
                                    shadeClose: true,
                                    maxmin: true,
                                    skin: 'custom-layer',
                                    content: `
                                        <div class="generate-result-container">
                                            <div class="generate-result-info">
                                                <div class="generate-result-meta">
                                                    <span>写作类型：${$('select[name="writing_type"] option:selected').text() || localStorage.getItem('lastWritingType') || '未指定'}</span>
                                                    <span>标签数量：${window.globalTags ? window.globalTags.size : 0}</span>
                                                    <button class="layui-btn layui-btn-sm layui-btn-normal" id="regenerateContent">
                                                        <i class="layui-icon layui-icon-refresh"></i> 重新生成
                                                    </button>
                                                </div>
                                                <div class="generate-result-tags">
                                                    ${window.globalTags ? Array.from(window.globalTags).map(([tag, info]) => `
                                                        <span class="generate-result-tag">${info ? `${tag}（${info}）` : tag}</span>
                                                    `).join('') : ''}
                                                </div>
                                            </div>
                                            <div class="generate-result-content markdown-body">
                                                ${marked.parse(this.generationStatus.content)}
                                            </div>
                                        </div>
                                    `,
                                    success: function(layero, index) {
                                        // 添加重新生成按钮的点击事件
                                        $(layero).find('#regenerateContent').on('click', function() {
                                            // 获取上次请求的数据
                                            const lastRequestData = JSON.parse(localStorage.getItem('lastGenerationRequest') || '{}');
                                            
                                            if (!lastRequestData.tags || !lastRequestData.writing_type) {
                                                layer.msg('无法获取上次生成的参数，请返回重新生成');
                                                return;
                                            }
                                            
                                            // 显示简单的文本提示，不使用加载动画
                                            layer.msg('正在后台重新生成内容...', {
                                                time: 3000  // 3秒后自动关闭
                                            });
                                        
                                            // 重新发送请求
                                            $.ajax({
                                                url: '/api/tags/generate',
                                                type: 'POST',
                                                data: JSON.stringify(lastRequestData),
                                                contentType: 'application/json',
                                                skipLoading: true,
                                                success: function(newRes) {
                                                    if (newRes.code === 0) {
                                                        // 更新内容
                                                        $(layero).find('.generate-result-content').html(marked.parse(newRes.data));
                                                        
                                                        // 更新生成状态
                                                        if (window.notificationSystem) {
                                                            window.notificationSystem.setGenerationStatus({
                                                                content: newRes.data,
                                                                isCompleted: true,
                                                                isGenerating: false
                                                            });
                                                        }
                                                        
                                                        console.log('内容重新生成成功');
                                                        layer.msg('内容已重新生成');
                                                    } else {
                                                        layer.msg(newRes.msg || '重新生成失败');
                                                        console.error('重新生成失败:', newRes.msg);
                                                    }
                                                },
                                                error: function(xhr, status, error) {
                                                    layer.msg('请求失败，请重试');
                                                    console.error('重新生成请求失败:', status, error);
                                                }
                                            });
                                        });
                                    }
                                });
                            }
                        }
                    }
                ]
            );
        },
        
        // 重置生成状态
        resetGenerationStatus: function() {
            console.log('重置生成状态');
            this.generationStatus = {
                isGenerating: false,
                isCompleted: false,
                content: null,
                notified: false,
                taskId: null
            };
            localStorage.setItem('generationStatus', JSON.stringify(this.generationStatus));
        },
        
        // 检查待处理的生成任务
        checkPendingGenerations: function() {
            console.log('检查待处理的生成任务');
            
            // 从本地存储获取生成状态
            const savedStatus = localStorage.getItem('generationStatus');
            if (!savedStatus) {
                return;
            }
            
            try {
                const status = JSON.parse(savedStatus);
                
                // 如果有正在生成的任务，检查其状态
                if (status.isGenerating && status.taskId && !status.isCompleted) {
                    console.log('发现未完成的生成任务，任务ID:', status.taskId);
                    
                    // 检查任务状态
                    $.ajax({
                        url: `/api/generation/status/${status.taskId}`,
                        type: 'GET',
                        success: (res) => {
                            if (res.code === 0) {
                                console.log('获取到任务状态:', res.status);
                                
                                if (res.status === 'completed') {
                                    // 更新生成状态
                                    this.setGenerationStatus({
                                        isGenerating: false,
                                        isCompleted: true,
                                        content: res.content,
                                        notified: false,
                                        taskId: status.taskId
                                    });
                                } else if (res.status === 'failed') {
                                    // 更新为失败状态
                                    this.setGenerationStatus({
                                        isGenerating: false,
                                        isCompleted: false,
                                        taskId: status.taskId
                                    });
                                    
                                    // 显示失败通知
                                    this.showNotification(
                                        '内容生成失败',
                                        res.error || '生成过程中发生错误',
                                        'error',
                                        [{
                                            text: '查看详情',
                                            action: 'view_error',
                                            handler: () => {
                                                window.location.href = `/generation/result/${status.taskId}`;
                                            }
                                        }]
                                    );
                                }
                                // 如果仍在处理中，不做任何操作
                            }
                        },
                        error: (xhr, status, error) => {
                            console.error('检查任务状态失败:', status, error);
                        }
                    });
                }
            } catch (e) {
                console.error('解析生成状态时出错:', e);
            }
        },
        
        // 在notificationSystem对象中添加销毁方法
        destroy: function() {
            // 清除定时器
            if (this.checkIntervalId) {
                clearInterval(this.checkIntervalId);
                this.checkIntervalId = null;
            }
            
            // 重置初始化标志
            this.initialized = false;
            
            console.log('通知系统已销毁');
        }
    };
    
    // 配置layui，禁用默认字体图标
    layui.config({
        font: false
    });
    
    // 监听写作类型选择
    form.on('select(writingType)', function(data){
        if(data.value) {
            layer.msg('已选择写作类型：' + data.elem[data.elem.selectedIndex].text);
            window.selectedWritingType = data.value;
        }
    });
    
    // 全局标签存储,用于存储标签及其附加信息
    window.globalTags = new Map();
    
    // 设置标签过期时间（30分钟）
    const TAG_EXPIRY_TIME = 30 * 60 * 1000;
    
    // 从 localStorage 加载已保存的标签，并检查是否过期
    function loadSavedTags() {
        const savedData = localStorage.getItem('selectedTagsData');
        if (savedData) {
            const data = JSON.parse(savedData);
            const now = new Date().getTime();
            
            if (now - data.timestamp < TAG_EXPIRY_TIME) {
                data.tags.forEach(([tag, info]) => window.addGlobalTag(tag, info));
            } else {
                localStorage.removeItem('selectedTagsData');
                layer.msg('标签已过期，已自动清除');
            }
        }
    }
    
    // 保存标签到 localStorage
    function saveTagsToStorage() {
        const data = {
            tags: Array.from(window.globalTags.entries()),
            timestamp: new Date().getTime()
        };
        localStorage.setItem('selectedTagsData', JSON.stringify(data));
    }
    
    // 检查过期标签
    function checkExpiredTags() {
        const savedData = localStorage.getItem('selectedTagsData');
        if (savedData) {
            const data = JSON.parse(savedData);
            const now = new Date().getTime();
            
            if (now - data.timestamp >= TAG_EXPIRY_TIME) {
                localStorage.removeItem('selectedTagsData');
                window.globalTags.clear();
                updateSelectedTagsDisplay();
                layer.msg('标签已过期，已自动清除');
            }
        }
    }
    
    // 更新已选标签显示
    function updateSelectedTagsDisplay() {
        const container = $('#selectedTags');
        container.empty();
        
        window.globalTags.forEach((info, tag) => {
            const tagElement = $('<span class="selected-tag"></span>')
                .text(info ? `${tag}（${info}）` : tag)
                .append('<span class="close-btn">×</span>');
            
            tagElement.find('.close-btn').click(function() {
                window.globalTags.delete(tag);
                updateSelectedTagsDisplay();
                saveTagsToStorage();
            });
            
            container.append(tagElement);
        });
    }
    
    // 添加全局标签方法
    window.addGlobalTag = function(tag, additionalInfo = null) {
        if (!window.globalTags.has(tag)) {
            window.globalTags.set(tag, additionalInfo);
            updateSelectedTagsDisplay();
            saveTagsToStorage();
        }
    };
    
    // 加载推荐标签
    function loadRecommendedTags() {
        $.ajax({
            url: '/api/tags/recommended',
            type: 'GET',
            skipLoading: true,  // 使用自定义属性标记跳过加载动画
            success: function(res) {
                if (res && res.code === 0 && Array.isArray(res.data)) {
                    const container = $('#recommendedTags');
                    container.empty();
                    
                    res.data.forEach(tag => {
                        if (tag) {
                            const tagElement = $('<span class="recommended-tag draggable-tag"></span>')
                                .text(tag)
                                .attr('data-tag', tag);
                            container.append(tagElement);
                        }
                    });
                    
                    initDraggable();
                } else {
                    console.warn('加载推荐标签失败或返回数据格式不正确');
                }
            },
            error: function(xhr, status, error) {
                console.error('加载推荐标签请求失败:', error);
            }
        });
    }
    
    // 初始化拖拽功能
    function initDraggable() {
        $('.draggable-tag').draggable({
            helper: 'clone',
            revert: 'invalid',
            zIndex: 1000
        });
    }

    // 初始化评论标签拖拽
    function initCommentTagsDraggable() {
        $('.comment-tag').draggable({
            helper: 'clone',
            revert: 'invalid',
            zIndex: 1000,
            start: function(event, ui) {
            $(ui.helper).addClass('dragging');
        },
            stop: function(event, ui) {
                $(ui.helper).removeClass('dragging');
            }
        });
    }

    // 初始化3D卡片效果
    function init3DCardEffect() {
        document.querySelectorAll('.book-card').forEach(card => {
            // 鼠标移动效果
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 10;
                const rotateY = -(x - centerX) / 10;
                
                card.querySelector('.book-card-inner').style.transform = 
                    `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
            });
            
            // 鼠标离开效果
            card.addEventListener('mouseleave', () => {
                const inner = card.querySelector('.book-card-inner');
                inner.style.transform = 'rotateX(0) rotateY(0)';
            });
            
            // 触摸设备支持 - 添加被动标志
            card.addEventListener('touchmove', e => {
                e.preventDefault();
                const touch = e.touches[0];
                const rect = card.getBoundingClientRect();
                const x = touch.clientX - rect.left;
                const y = touch.clientY - rect.top;
                
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                
                const rotateX = (y - centerY) / 10;
                const rotateY = -(x - centerX) / 10;
                
                card.querySelector('.book-card-inner').style.transform = 
                    `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
            }, { passive: false }); // 明确指定非被动模式，因为我们使用了preventDefault
            
            // 触摸结束效果
            card.addEventListener('touchend', () => {
                const inner = card.querySelector('.book-card-inner');
                inner.style.transform = 'rotateX(0) rotateY(0)';
            }, { passive: true }); // 被动模式
        });
    }

    
    // 页面加载时初始化
    $(document).ready(function() {
        const panel = $('.left-tags-panel');
        const toggle = $('.panel-toggle');
        const icon = toggle.find('.layui-icon');
        const body = $('.layui-body');
        
        // 更新面板状态的函数
        function updatePanelState(collapsed) {
            if (collapsed) {
                panel.addClass('collapsed');
                icon.removeClass('layui-icon-left').addClass('layui-icon-right');
                body.css('left', '0');
                toggle.css('left', '0');  // 更新按钮位置
            } else {
                panel.removeClass('collapsed');
                icon.removeClass('layui-icon-right').addClass('layui-icon-left');
                body.css('left', '250px');
                toggle.css('left', '250px');  // 更新按钮位置
            }
        }
        
        // 点击切换面板状态
        toggle.click(function() {
            const willCollapse = !panel.hasClass('collapsed');
            updatePanelState(willCollapse);
            
            // 触发resize事件以重新计算布局
            setTimeout(function() {
                $(window).trigger('resize');
            }, 300);
        });
        
        // 监听窗口大小变化
        $(window).resize(function() {
            if ($(window).width() <= 768) {
                updatePanelState(true);  // 移动端默认收起
            } else {
                // 如果是从移动端变为桌面端，可以选择是否自动展开
                // updatePanelState(false);  // 取消注释这行将在桌面端自动展开
            }
        });
        
        // 初始化面板状态
        if ($(window).width() <= 768) {
            updatePanelState(true);
        }
        
        loadSavedTags();
        loadRecommendedTags();
        initCommentTagsDraggable();
        init3DCardEffect();
        
        // 定期检查过期标签
        setInterval(checkExpiredTags, 60000);
        
        // 设置标签栏
        $('#selectedTags').droppable({
            accept: '.draggable-tag, .comment-tag',  
            drop: function(event, ui) {
                var tag = ui.draggable.data('tag') || ui.draggable.text().trim();
                window.addGlobalTag(tag);
                layer.msg('已添加标签：' + tag);
            }
        });

        // 页面离开前保存状态
        $(window).on('beforeunload', function() {
            // 如果正在生成内容，保存状态
            if (window.notificationSystem && window.notificationSystem.generationStatus.isGenerating) {
                localStorage.setItem('generationStatus', JSON.stringify(window.notificationSystem.generationStatus));
            }
        });

        // 确保通知系统在页面加载时初始化
        if (!$('#notificationContainer').length) {
            $('body').append('<div class="notification-container" id="notificationContainer"></div>');
        }
        
        // 检查通知系统是否已初始化
        if (!window.notificationSystem) {
            console.warn('通知系统未初始化，正在重新初始化...');
            // 这里可以重新初始化通知系统
        }
    });
    
    // 刷新推荐标签
    $('#refreshTags').click(function() {
        loadRecommendedTags();
        layer.msg('已刷新推荐标签');
    });
    
    // 清空标签
    $('#clearTags').click(function() {
        window.globalTags.clear();
        updateSelectedTagsDisplay();
        localStorage.removeItem('selectedTagsData');
        layer.msg('已清空所有标签');
    });

    // 修改全局 AJAX 请求处理
    $(document).ajaxStart(function(event) {
        // 检查是否有正在进行的非skipLoading请求
        if (!window.hasSkipLoadingRequest) {
            $('.loading').show();
        }
    });

    $(document).ajaxStop(function() {
        // 所有请求完成后隐藏加载动画
        $('.loading').hide();
        window.hasSkipLoadingRequest = false;
    });

    // 添加 AJAX 拦截器
    $.ajaxPrefilter(function(options, originalOptions, jqXHR) {
        // 如果请求标记为跳过加载动画
        if (options.skipLoading) {
            window.hasSkipLoadingRequest = true;
            
            // 确保这个请求不会触发加载动画
            const oldBeforeSend = options.beforeSend;
            options.beforeSend = function(xhr) {
                $('.loading').hide();
                if (oldBeforeSend) return oldBeforeSend(xhr);
            };
            
            return;
        }
        
        // 显示加载动画
        $('.loading').show();
        
        // 添加完成回调
        const complete = options.complete;
        options.complete = function(jqXHR, textStatus) {
            // 只有当没有其他skipLoading请求时才隐藏加载动画
            if (!window.hasSkipLoadingRequest) {
                $('.loading').hide();
            }
            
            // 调用原始的完成回调
            if (complete) {
                complete(jqXHR, textStatus);
            }
        };
    });

    // 图表响应式处理
    $(window).on('resize', function() {
        $('[id$="Chart"],[id$="Cloud"],[id$="Pie"]').each(function() {
            var instance = echarts.getInstanceByDom(this);
            if(instance) {
                instance.resize();
            }
        });
    });
    
    // 为所有标签添加点击事件
    $(document).on('click', '.draggable-tag', function() {
        var tag = $(this).data('tag') || $(this).text().trim();
        window.addGlobalTag(tag);
        layer.msg('已添加标签：' + tag); 
    });
    
    // 监听动态添加的元素
    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                initDraggable();
                initCommentTagsDraggable();
                init3DCardEffect();
            }
        });
    });

    // 确保目标元素存在
    var targetNode = document.querySelector('.main-content');
    if (targetNode) {
        var config = { childList: true, subtree: true };
        observer.observe(targetNode, config);
    }

    // 自定义标签按钮点击事件
    $('#addCustomTag').click(function(e) {
        e.stopPropagation();
        const inputGroup = $('.custom-tag-input-group');
        
        // 计算位置
        const buttonPos = $(this).offset();
        const buttonHeight = $(this).outerHeight();
        
        // 设置输入框位置
        inputGroup.css({
            'position': 'fixed',
            'top': buttonPos.top + buttonHeight + 5,
            'left': buttonPos.left,
            'z-index': 1000
        }).toggle();
    
        if(inputGroup.is(':visible')) {
            $('#customTagInput').focus();
            // 显示遮罩层
            $('<div class="custom-tag-overlay"></div>')
                .appendTo('body')
                .css({
                    'position': 'fixed',
                    'top': 0,
                    'left': 0,
                    'right': 0,
                    'bottom': 0,
                    'background': 'rgba(0,0,0,0.3)',
                    'z-index': 999
                });
        } else {
            // 移除遮罩层
            $('.custom-tag-overlay').remove();
        }
    });

    // 添加自定义标签
    $('.add-custom-tag-btn').click(function() {
        var tagInput = $('#customTagInput').val().trim();
        if(tagInput) {
            // 检查是否包含附加信息
            const match = tagInput.match(/^(.*?)（(.*?)）$/);
            if (match) {
                const [_, tag, info] = match;
                window.addGlobalTag(tag.trim(), info.trim());
                layer.msg('已添加带说明的标签：' + tag.trim());
            } else {
                window.addGlobalTag(tagInput);
                layer.msg('已添加标签：' + tagInput);
            }
            $('#customTagInput').val('');
            $('.custom-tag-input-group').hide();
            $('.custom-tag-overlay').remove();
        }
    });

    // 取消按钮点击事件
    $('.cancel-custom-tag-btn').click(function() {
        $('#customTagInput').val('');
        $('.custom-tag-input-group').hide();
        $('.custom-tag-overlay').remove();
        $('.tag-input-tips').hide(); 
    });

    // 自定义标签输入框回车事件
    $('#customTagInput').keypress(function(e) {
        if(e.which == 13) {
            $('.add-custom-tag-btn').click();
        }
    });
    // 输入框获得焦点时显示提示
    $('#customTagInput').on('focus', function() {
        $('.tag-input-tips').fadeIn(200);
    });

    // 输入框失去焦点时隐藏提示
    $('#customTagInput').on('blur', function() {
        // 延迟隐藏，让用户有时间阅读提示
        setTimeout(function() {
            if (!$('#customTagInput').is(':focus')) {
                $('.tag-input-tips').fadeOut(200);
            }
        }, 200);
    });

    // 点击遮罩层或其他地方时隐藏输入框
    $(document).on('click', '.custom-tag-overlay', function() {
        $('.custom-tag-input-group').hide();
        $('.custom-tag-overlay').remove();
    });

    // 阻止输入框内的点击事件冒泡
    $('.custom-tag-input-group').click(function(e) {
        e.stopPropagation();
    });


    // 点击其他地方时隐藏输入框
    $(document).click(function(e) {
        if(!$(e.target).closest('.custom-tag-input-group, #addCustomTag').length) {
            $('.custom-tag-input-group').hide();
        }
    });

    // 图表工具类
    window.chartUtils = {
        // 初始化词云图
        initWordCloud: function(elementId, data, config = {}) {
            const chart = echarts.init(document.getElementById(elementId));
            const option = {
                series: [{
                    type: 'wordCloud',
                    shape: 'circle',
                    left: 'center',
                    top: 'center',
                    width: '90%',
                    height: '90%',
                    right: null,
                    bottom: null,
                    sizeRange: [12, 60],
                    rotationRange: [-90, 90],
                    rotationStep: 45,
                    gridSize: 8,
                    drawOutOfBound: false,
                    textStyle: {
                        fontFamily: 'sans-serif',
                        fontWeight: 'bold',
                        color: function () {
                            return 'rgb(' + [
                                Math.round(Math.random() * 160),
                                Math.round(Math.random() * 160),
                                Math.round(Math.random() * 160)
                            ].join(',') + ')';
                        }
                    },
                    emphasis: {
                        focus: 'self',
                        textStyle: {
                            shadowBlur: 10,
                            shadowColor: '#333'
                        }
                    },
                    data: data
                }],
                
            };
            chart.setOption(option);
            return chart;
        }
    };

    // 生成内容按钮点击事件
    $('#generateContent').click(function() {
        try {
            console.log('点击生成内容按钮');
            // 获取写作类型
            const writingType = $('select[name="writing_type"]').val();
            if (!writingType) {
                layer.msg('请选择写作类型');
                return;
            }
            
            // 保存写作类型到本地存储，用于跨页面显示
            localStorage.setItem('lastWritingType', $('select[name="writing_type"] option:selected').text());
            console.log('保存写作类型:', $('select[name="writing_type"] option:selected').text());
            
            // 获取标签
            if (!window.globalTags || window.globalTags.size === 0) {
                layer.msg('请至少添加一个标签');
                return;
            }
            
            // 准备请求数据
            const tags = [];
            const tagInfos = [];
            
            window.globalTags.forEach((info, tag) => {
                if (info) {
                    tagInfos.push({tag: tag, info: info});
                } else {
                    tags.push(tag);
                }
            });
            
            const requestData = {
                tags: tags,
                tag_infos: tagInfos,
                writing_type: writingType
            };
            
            console.log('准备发送请求数据:', requestData);
            
            // 保存请求数据到本地存储，用于重新生成
            localStorage.setItem('lastGenerationRequest', JSON.stringify(requestData));
            
            // 重置之前的生成状态
            if (window.notificationSystem) {
                console.log('重置之前的生成状态');
                window.notificationSystem.resetGenerationStatus();
            }
            
            // 更新生成状态为正在生成
            if (window.notificationSystem) {
                console.log('更新生成状态为正在生成');
                window.notificationSystem.setGenerationStatus({
                    isGenerating: true,
                    isCompleted: false,
                    notified: false
                });
            }
            
            // 显示简单的文本提示，不使用加载动画
            layer.msg('正在后台生成内容，完成后将通知您...', {
                time: 3000  // 3秒后自动关闭
            });
            
            // 发送请求
            $.ajax({
                url: '/api/tags/generate',
                type: 'POST',
                data: JSON.stringify(requestData),
                contentType: 'application/json',
                skipLoading: true,
                success: function(res) {
                    if (res.code === 0) {
                        console.log('生成请求已发送，任务ID:', res.task_id);
                        
                        // 保存任务ID到生成状态
                        if (window.notificationSystem) {
                            window.notificationSystem.setGenerationStatus({
                                taskId: res.task_id
                            });
                        }
                        
                        // 启动轮询检查任务状态
                        startPollingGenerationStatus(res.task_id);
                    } else {
                        layer.msg(res.msg || '生成失败');
                        console.error('生成失败:', res.msg);
                        
                        // 更新生成状态为失败
                        if (window.notificationSystem) {
                            console.log('更新生成状态为失败');
                            window.notificationSystem.setGenerationStatus({
                                isGenerating: false,
                                isCompleted: false
                            });
                        }
                    }
                },
                error: function(xhr, status, error) {
                    layer.msg('请求失败，请重试');
                    console.error('请求失败:', status, error);
                    
                    // 更新生成状态为失败
                    if (window.notificationSystem) {
                        console.log('更新生成状态为失败');
                        window.notificationSystem.setGenerationStatus({
                            isGenerating: false,
                            isCompleted: false
                        });
                    }
                }
            });
        } catch (error) {
            console.error('生成内容时发生错误:', error);
            layer.msg('生成内容时发生错误，请刷新页面后重试');
        }
    });

    // 添加轮询检查生成状态的函数
    function startPollingGenerationStatus(taskId) {
        console.log('开始轮询检查生成状态，任务ID:', taskId);
        
        // 设置轮询间隔（毫秒）
        const pollingInterval = 3000;
        let pollingCount = 0;
        const maxPollingCount = 60; // 最多轮询60次（3分钟）
        
        // 创建轮询函数
        function checkStatus() {
            // 增加计数
            pollingCount++;
            
            // 如果超过最大轮询次数，停止轮询
            if (pollingCount > maxPollingCount) {
                console.log('轮询次数超过限制，停止轮询');
                return;
            }
            
            $.ajax({
                url: `/api/generation/status/${taskId}`,
                type: 'GET',
                success: function(res) {
                    if (res.code === 0) {
                        // 只在状态变化时记录日志
                        if (pollingCount === 1 || pollingCount % 10 === 0) {
                            console.log(`轮询第${pollingCount}次，生成状态:`, res.status);
                        }
                        
                        if (res.status === 'completed') {
                            // 生成完成，更新状态
                            console.log('内容生成完成，停止轮询');
                            if (window.notificationSystem) {
                                window.notificationSystem.setGenerationStatus({
                                    isGenerating: false,
                                    isCompleted: true,
                                    content: res.content,
                                    notified: false,
                                    taskId: taskId
                                });
                            }
                            // 停止轮询
                            return;
                        } else if (res.status === 'failed') {
                            // 生成失败
                            console.log('内容生成失败，停止轮询');
                            layer.msg('内容生成失败: ' + (res.error || '未知错误'));
                            if (window.notificationSystem) {
                                window.notificationSystem.setGenerationStatus({
                                    isGenerating: false,
                                    isCompleted: false
                                });
                            }
                            // 停止轮询
                            return;
                        } else {
                            // 继续轮询，但增加间隔时间
                            const nextInterval = Math.min(pollingInterval * (1 + Math.floor(pollingCount / 10)), 30000);
                            setTimeout(checkStatus, nextInterval);
                        }
                    } else {
                        // 请求出错
                        console.error('检查生成状态失败:', res.msg);
                        // 继续轮询，但增加间隔时间
                        setTimeout(checkStatus, pollingInterval * 2);
                    }
                },
                error: function(xhr, status, error) {
                    console.error('检查生成状态请求失败:', status, error);
                    // 继续轮询，但增加间隔时间
                    setTimeout(checkStatus, pollingInterval * 2);
                }
            });
        }
        
        // 开始第一次检查
        setTimeout(checkStatus, pollingInterval);
    }
});