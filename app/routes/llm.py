"""
LLM相关路由模块
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from app.utils.auth import require_api_key, local_access_only
from app.config import LLM_CONFIG

# 创建蓝图
llm_bp = Blueprint('llm', __name__)

@llm_bp.route('/models', methods=['GET'])
@require_api_key
def list_llm_models():
    """获取可用的LLM模型列表"""
    try:
        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403
        
        # 导入LLM服务
        from app.services.llm_service import get_available_models
        
        # 获取可用模型
        models = get_available_models()
        
        return jsonify({
            'models': models,
            'default_model': LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat')
        })
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'获取模型列表失败: {str(e)}'}), 500

@llm_bp.route('/chat', methods=['POST'])
@require_api_key
def llm_chat():
    """LLM聊天接口"""
    try:
        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400
        
        # 验证必要字段
        if 'messages' not in data or not isinstance(data['messages'], list) or not data['messages']:
            return jsonify({'error': '消息列表不能为空'}), 400
        
        # 导入LLM服务
        from app.services.llm_service import chat_completion
        
        # 获取参数
        model = data.get('model', LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'))
        temperature = data.get('temperature', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('temperature', 0.7))
        max_tokens = data.get('max_tokens', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('max_tokens', 1000))
        top_p = data.get('top_p', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('top_p', 0.9))
        
        # 调用LLM服务
        result = chat_completion(
            messages=data['messages'],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        
        return jsonify(result)
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'LLM聊天请求失败: {str(e)}'}), 500

@llm_bp.route('/generate', methods=['POST'])
@require_api_key
def llm_generate():
    """LLM内容生成接口 - 简化版，只需要提供提示文本"""
    try:
        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            return jsonify({'error': 'LLM功能未启用'}), 403
        
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({'error': '请求数据无效'}), 400
        
        # 验证必要字段
        if 'prompt' not in data or not data['prompt']:
            return jsonify({'error': '提示文本不能为空'}), 400
        
        # 导入LLM服务
        from app.services.llm_service import chat_completion
        
        # 获取参数
        model = data.get('model', LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'))
        temperature = data.get('temperature', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('temperature', 0.7))
        # 增加默认的max_tokens，以支持生成更多内容
        max_tokens = data.get('max_tokens', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('max_tokens', 2000))
        top_p = data.get('top_p', LLM_CONFIG.get('DEFAULT_PARAMS', {}).get('top_p', 0.9))
        
        # 构建系统提示，指导模型生成结构化内容
        system_message = {
            "role": "system",
            "content": "你是一个内容生成助手，擅长生成结构化的内容。请严格按照用户指定的格式生成内容，不要添加额外的解释或说明。"
        }
        
        # 构建消息，添加系统提示
        messages = [
            system_message,
            {"role": "user", "content": data['prompt']}
        ]
        
        # 调用LLM服务
        result = chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p
        )
        
        # 简化响应
        if 'choices' in result and len(result['choices']) > 0 and 'message' in result['choices'][0]:
            return jsonify({
                'text': result['choices'][0]['message'].get('content', ''),
                'model': result.get('model', model)
            })
        
        return jsonify(result)
    except ImportError as e:
        return jsonify({'error': f'LLM服务模块加载失败: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'LLM生成请求失败: {str(e)}'}), 500

# LLM管理界面
@llm_bp.route('/dashboard', methods=['GET'])
@local_access_only
def llm_dashboard():
    """LLM管理界面"""
    try:
        # 检查LLM功能是否启用
        if not LLM_CONFIG.get('ENABLED', False):
            flash('LLM功能未启用，请在config.py中启用', 'error')
            return redirect(url_for('main.index'))
        
        # 导入LLM服务
        from app.services.llm_service import get_available_models
        
        # 获取可用模型
        models = get_available_models()
        
        return render_template(
            'llm.html',
            models=models,
            default_model=LLM_CONFIG.get('DEFAULT_MODEL', 'deepseek-chat'),
            config=LLM_CONFIG
        )
    except ImportError as e:
        flash(f'LLM服务模块加载失败: {str(e)}', 'error')
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f'获取LLM信息失败: {str(e)}', 'error')
        return redirect(url_for('main.index'))
