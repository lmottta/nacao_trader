#!/bin/bash
# Script para criar uma nova feature branch seguindo o GitFlow

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

if [ $# -eq 0 ]; then
  echo -e "${RED}Erro: Nenhum nome de feature fornecido.${NC}"
  echo "Uso: $0 nome-da-feature"
  exit 1
fi

# Normaliza o nome da feature (minúsculas, traços em vez de espaços)
FEATURE_NAME=$(echo "$1" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
BRANCH_NAME="feature/$FEATURE_NAME"

# Verifica se estamos em um repositório git
if [ ! -d .git ]; then
  echo -e "${RED}Erro: Não está em um repositório Git.${NC}"
  echo "Execute este script na raiz do projeto."
  exit 1
fi

# Verifica se a branch já existe
if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
  echo -e "${RED}Erro: Branch '$BRANCH_NAME' já existe.${NC}"
  exit 1
fi

# Atualiza o repositório
echo -e "${YELLOW}Atualizando o repositório...${NC}"
git fetch --all

# Verifica se a branch develop existe
if ! git show-ref --verify --quiet refs/heads/develop; then
  echo -e "${RED}Erro: Branch 'develop' não existe.${NC}"
  echo "Execute o script setup-gitflow.sh primeiro para configurar o GitFlow."
  exit 1
fi

# Cria a nova feature branch
echo -e "${YELLOW}Criando nova feature branch '$BRANCH_NAME' baseada em 'develop'...${NC}"
git checkout develop
git pull origin develop
git checkout -b $BRANCH_NAME

# Cria arquivo de changelog para a feature
CHANGELOG_FILE="doc/features/$FEATURE_NAME.md"
mkdir -p doc/features
cat > $CHANGELOG_FILE << EOF
# Feature: ${FEATURE_NAME}

## Descrição
[Descreva a feature aqui]

## Tarefas
- [ ] Tarefa 1
- [ ] Tarefa 2
- [ ] Tarefa 3

## Alterações
- Arquivo 1: Descrição da alteração
- Arquivo 2: Descrição da alteração

## Testes
- [ ] Teste 1
- [ ] Teste 2

## Observações
[Observações adicionais]

## Pull Request
- [ ] Criado em: [DATA]
- [ ] Revisado por: [REVISOR]
- [ ] Aprovado em: [DATA]
EOF

# Adiciona o arquivo de changelog ao Git
git add $CHANGELOG_FILE
git commit -m "Inicia feature: $FEATURE_NAME"

echo -e "\n${GREEN}Feature branch '$BRANCH_NAME' criada com sucesso!${NC}"
echo -e "Arquivo de changelog criado em: ${YELLOW}$CHANGELOG_FILE${NC}"
echo -e "\nPróximos passos:"
echo -e "1. Implemente as alterações para a feature"
echo -e "2. Atualize o arquivo de changelog conforme necessário"
echo -e "3. Quando concluído, use: ${YELLOW}git checkout develop && git merge $BRANCH_NAME${NC}"
echo -e "4. Crie um Pull Request para revisão da feature" 