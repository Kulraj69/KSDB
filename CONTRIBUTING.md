# Contributing to KSdb

First off, thank you for considering contributing to KSdb! 🎉

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check the existing issues. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include logs and error messages**

### 💡 Suggesting Features

Feature requests are welcome! Please provide:

- **A clear and descriptive title**
- **A detailed description of the proposed feature**
- **Why this feature would be useful**
- **Examples of how it would work**

### 🔧 Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Make your changes**
3. **Add tests** if applicable
4. **Update documentation** if you changed APIs
5. **Ensure tests pass**
6. **Submit a pull request**

#### Pull Request Guidelines:

- Follow the existing code style
- Write clear commit messages
- Update the README.md if needed
- Add yourself to CONTRIBUTORS.md

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/KSDB.git
cd KSdb

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt

# Run tests
python -m pytest tests/

# Run the server
cd server
python main.py
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for high code coverage

## Areas We Need Help With

- 🚀 **Performance optimization** - Make search faster
- 🔐 **Authentication** - Add API key support
- 📊 **Advanced filtering** - Support `$gt`, `$lt`, `$in` operators
- 🎨 **Dashboard** - Build a web UI for KSdb
- 📚 **Documentation** - Improve guides and examples
- 🧪 **Testing** - Add more test coverage
- 🌐 **Integrations** - LangChain, LlamaIndex, etc.

## Questions?

Feel free to open an issue with the `question` label!

---

Thank you for contributing! 🙏
