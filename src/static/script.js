// DOM 元素
const elements = {
    dropZone: document.getElementById('dropZone'),
    fileInput: document.getElementById('fileInput'),
    fileInfo: document.getElementById('fileInfo'),
    fileName: document.getElementById('fileName'),
    fileSize: document.getElementById('fileSize'),
    removeFile: document.getElementById('removeFile'),
    progressContainer: document.getElementById('uploadProgress'),
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    submitButton: document.getElementById('submitButton'),
    uploadForm: document.getElementById('uploadForm'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
};

// 配置
const config = {
    maxFileSize: 10 * 1024 * 1024, // 10MB
    allowedTypes: ['.md'],
};

// 工具函数
const utils = {
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    showNotification(message, type = 'info') {
        elements.toastMessage.textContent = message;
        elements.toast.className = `toast ${type}`;
        elements.toast.classList.remove('hidden');
        setTimeout(() => {
            elements.toast.classList.add('hidden');
        }, 3000);
    },
};

// 文件处理
const fileHandler = {
    validateFile(file) {
        if (!file) {
            throw new Error('请选择文件');
        }
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        if (!config.allowedTypes.includes(fileExtension)) {
            throw new Error('只支持上传 MD 文件');
        }
        if (file.size > config.maxFileSize) {
            throw new Error(`文件大小不能超过 ${utils.formatFileSize(config.maxFileSize)}`);
        }
        return true;
    },

    updateFileInfo(file) {
        elements.fileName.textContent = file.name;
        elements.fileSize.textContent = utils.formatFileSize(file.size);
        elements.fileInfo.classList.remove('hidden');
        elements.submitButton.disabled = false;
    },

    clearFileInfo() {
        elements.fileInput.value = '';
        elements.fileInfo.classList.add('hidden');
        elements.progressContainer.classList.add('hidden');
        elements.submitButton.disabled = true;
    }
};

// 上传管理
const uploadManager = {
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.blob();
        } catch (error) {
            throw new Error('上传失败: ' + error.message);
        }
    }
};

// 事件处理
const eventHandlers = {
    onDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.add('dragover');
    },

    onDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.remove('dragover');
    },

    onDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        elements.dropZone.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file) {
            elements.fileInput.files = e.dataTransfer.files;
            eventHandlers.onFileSelect({ target: { files: [file] } });
        }
    },

    onFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            try {
                fileHandler.validateFile(file);
                fileHandler.updateFileInfo(file);
            } catch (error) {
                utils.showNotification(error.message, 'error');
                fileHandler.clearFileInfo();
            }
        }
    },

    onRemoveFile(e) {
        e.preventDefault();
        fileHandler.clearFileInfo();
    },

    async onFormSubmit(e) {
        e.preventDefault();
        const file = elements.fileInput.files[0];
        
        if (!file) {
            utils.showNotification('请选择文件', 'error');
            return;
        }

        try {
            elements.submitButton.disabled = true;
            elements.progressContainer.classList.remove('hidden');
            utils.showNotification('文件上传中...', 'info');

            const blob = await uploadManager.uploadFile(file);
            
            // 下载处理后的文件
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `processed_${file.name}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            utils.showNotification('处理完成！文件已开始下载。', 'success');
        } catch (error) {
            console.error('Upload error:', error);
            utils.showNotification(error.message, 'error');
        } finally {
            elements.progressContainer.classList.add('hidden');
            elements.submitButton.disabled = false;
        }
    }
};

// 初始化
function initialize() {
    // 绑定拖放事件
    elements.dropZone.addEventListener('dragover', eventHandlers.onDragOver);
    elements.dropZone.addEventListener('dragleave', eventHandlers.onDragLeave);
    elements.dropZone.addEventListener('drop', eventHandlers.onDrop);

    // 绑定其他事件
    elements.fileInput.addEventListener('change', eventHandlers.onFileSelect);
    elements.removeFile.addEventListener('click', eventHandlers.onRemoveFile);
    elements.uploadForm.addEventListener('submit', eventHandlers.onFormSubmit);
}

// 当 DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', initialize);