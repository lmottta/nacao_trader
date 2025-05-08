#!/bin/bash
# Script para configurar o GitFlow no repositório

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configurando GitFlow para o projeto Nação Trader...${NC}"

# Verifica se estamos em um repositório git
if [ ! -d .git ]; then
  echo -e "${RED}Erro: Não está em um repositório Git.${NC}"
  echo "Execute este script na raiz do projeto."
  exit 1
fi

# Função para verificar se uma branch existe
branch_exists() {
  git rev-parse --verify --quiet $1 >/dev/null
  return $?
}

# Função para criar branch se não existir
create_branch_if_not_exists() {
  local branch_name=$1
  local base_branch=$2
  
  if branch_exists $branch_name; then
    echo -e "${GREEN}Branch '$branch_name' já existe.${NC}"
  else
    echo -e "Criando branch '$branch_name' baseada em '$base_branch'..."
    git checkout $base_branch
    git checkout -b $branch_name
    git push -u origin $branch_name
    echo -e "${GREEN}Branch '$branch_name' criada e enviada para o repositório remoto.${NC}"
  fi
}

# Assegura que temos as últimas atualizações
echo "Atualizando repositório..."
git fetch --all

# Verifica a branch main
if ! branch_exists main; then
  echo -e "${YELLOW}Branch 'main' não encontrada. Usando 'master' como base, se existir.${NC}"
  
  if branch_exists master; then
    echo "Renomeando 'master' para 'main'..."
    git checkout master
    git branch -m master main
    git push -u origin main
    git push origin --delete master
  else
    echo "Criando branch 'main'..."
    git checkout -b main
    git push -u origin main
  fi
fi

# Configura as branches do GitFlow
echo -e "\n${YELLOW}Configurando branches do GitFlow...${NC}"

# Cria branch develop baseada na main
create_branch_if_not_exists "develop" "main"

# Cria branch staging baseada na main
create_branch_if_not_exists "staging" "main"

# Configura proteções locais
echo -e "\n${YELLOW}Configurando ganchos locais de proteção...${NC}"

# Cria diretório para hooks se não existir
mkdir -p .git/hooks

# Cria o hook pre-push para proteção das branches principais
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash

protected_branches=("main" "staging")
current_branch=$(git symbolic-ref HEAD | sed -e 's,.*/\(.*\),\1,')

for branch in "${protected_branches[@]}"; do
  if [[ $current_branch == $branch ]]; then
    read -p "Você está prestes a enviar para a branch protegida '$branch'. Tem certeza? (s/N): " -n 1 -r < /dev/tty
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
      echo "Push para '$branch' cancelado."
      exit 1
    fi
  fi
done
exit 0
EOF

# Torna o hook executável
chmod +x .git/hooks/pre-push

echo -e "\n${GREEN}GitFlow configurado com sucesso!${NC}"
echo -e "Branches criadas: main, develop, staging"
echo -e "Hooks de proteção configurados."
echo -e "\nFluxo de trabalho recomendado:"
echo -e "1. Crie branches de feature a partir da 'develop': ${YELLOW}git checkout develop && git checkout -b feature/nova-funcionalidade${NC}"
echo -e "2. Após concluir, faça merge para 'develop': ${YELLOW}git checkout develop && git merge feature/nova-funcionalidade${NC}"
echo -e "3. Para homologação, envie para 'staging': ${YELLOW}git checkout staging && git merge develop${NC}"
echo -e "4. Para produção, envie para 'main': ${YELLOW}git checkout main && git merge staging${NC}"

# Volta para a branch develop
git checkout develop

echo -e "\n${GREEN}Pronto para começar o desenvolvimento!${NC}" 