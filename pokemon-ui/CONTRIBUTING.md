# Contributing to Fire Emblem AI

## Getting Started

Thank you for considering contributing to the Fire Emblem AI project! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- mGBA emulator
- Git
- Fire Emblem 8: The Sacred Stones ROM (legally obtained)

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/fe-ai.git
   cd fe-ai
   ```

2. **Check out develop branch**
   ```bash
   git checkout develop
   git pull origin develop
   ```

3. **Install dependencies**
   ```bash
   # Python dependencies
   pip install -r requirements.txt

   # React client dependencies
   cd fe-client
   npm install
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Place ROM file**
   ```bash
   # Copy your FE8.gba ROM to the roms/ directory
   cp /path/to/FE8.gba roms/
   ```

## Branching Workflow

### Creating a Feature Branch

Always create feature branches from the latest `develop` branch:

```bash
# Update develop
git checkout develop
git pull origin develop

# Create your feature branch
git checkout -b feature/your-feature-name

# Example feature branch names:
# feature/improve-combat-ai
# feature/add-support-conversations
# feature/optimize-pathfinding
```

### Working on Your Feature

1. **Make changes**
   ```bash
   # Edit files
   # Test locally
   ```

2. **Commit frequently**
   ```bash
   git add .
   git commit -m "feat: add tactical retreat logic"
   ```

3. **Keep branch updated**
   ```bash
   # Periodically sync with develop
   git fetch origin
   git rebase origin/develop
   ```

4. **Push your branch**
   ```bash
   git push -u origin feature/your-feature-name
   ```

### Creating a Pull Request

1. **Ensure tests pass**
   ```bash
   # Run Python tests
   python -m pytest

   # Run React tests
   cd fe-client && npm test
   ```

2. **Update documentation**
   - Add docstrings for new functions
   - Update README if needed
   - Document breaking changes

3. **Create PR on GitHub**
   - Target branch: `develop`
   - Fill out PR template
   - Link related issues
   - Request reviewers

## Commit Message Guidelines

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding missing tests
- `chore`: Changes to build process or auxiliary tools

### Scope Examples
- `ai`: AI logic changes
- `ui`: User interface changes
- `combat`: Combat system modifications
- `state`: Game state management
- `websocket`: WebSocket communication

### Good Commit Examples

```bash
# Feature
git commit -m "feat(ai): implement flanking strategy for cavalry units

Cavalry units now evaluate flanking opportunities when selecting targets.
Adds 15-20% combat effectiveness when executed properly.

Closes #123"

# Bug fix
git commit -m "fix(combat): correct critical hit calculation for killer weapons

Killer weapons were not properly adding their critical bonus.
Now correctly adds +30% critical rate."

# Performance
git commit -m "perf(state): optimize unit position lookups with spatial indexing

Replace O(n) unit position searches with O(1) hashmap lookups.
Reduces frame time by 40% in large battles."
```

## Code Style Guidelines

### Python Code Style

```python
"""
Module docstring describing purpose
"""
from typing import List, Optional, Dict
import logging

log = logging.getLogger(__name__)


class Unit:
    """
    Represents a Fire Emblem unit.

    Attributes:
        name: Unit's display name
        hp: Current hit points
        hp_max: Maximum hit points
    """

    def __init__(self, name: str, hp: int, hp_max: int):
        """Initialize a unit."""
        self.name = name
        self.hp = hp
        self.hp_max = hp_max

    def take_damage(self, damage: int) -> bool:
        """
        Apply damage to unit.

        Args:
            damage: Amount of damage to apply

        Returns:
            True if unit survives, False if defeated
        """
        self.hp = max(0, self.hp - damage)
        return self.hp > 0


def calculate_damage(
    attacker: Unit,
    defender: Unit,
    weapon: Weapon
) -> int:
    """
    Calculate combat damage.

    Args:
        attacker: Attacking unit
        defender: Defending unit
        weapon: Weapon being used

    Returns:
        Damage amount (minimum 0)
    """
    # Implementation here
    pass
```

### TypeScript/React Style

```typescript
// Component file: UnitCard.tsx
import React from 'react';
import { Unit } from '../types/gameTypes';

interface UnitCardProps {
  unit: Unit;
  selected: boolean;
  onSelect: (unit: Unit) => void;
}

/**
 * Displays a unit's information card
 */
export const UnitCard: React.FC<UnitCardProps> = ({
  unit,
  selected,
  onSelect
}) => {
  const handleClick = () => {
    onSelect(unit);
  };

  return (
    <div
      className={`unit-card ${selected ? 'selected' : ''}`}
      onClick={handleClick}
    >
      <h3>{unit.name}</h3>
      <p className="unit-class">{unit.unitClass}</p>
      <div className="hp-bar">
        <div
          className="hp-fill"
          style={{ width: `${(unit.hp / unit.hpMax) * 100}%` }}
        />
      </div>
    </div>
  );
};

// Helper function
export const calculateHPPercentage = (
  current: number,
  max: number
): number => {
  return Math.round((current / max) * 100);
};
```

## Testing Guidelines

### Writing Tests

#### Python Tests
```python
# test_combat.py
import pytest
from agent.game.fe_data import calculate_damage, Unit, Weapon

class TestCombatCalculations:
    def test_physical_damage_calculation(self):
        attacker = Unit(name="Eirika", strength=10)
        defender = Unit(name="Brigand", defense=5)
        weapon = Weapon(name="Iron Sword", might=5)

        damage = calculate_damage(attacker, defender, weapon)
        assert damage == 10  # (10 + 5) - 5

    def test_minimum_damage_is_zero(self):
        attacker = Unit(name="Weak", strength=1)
        defender = Unit(name="Knight", defense=20)
        weapon = Weapon(name="Iron Sword", might=5)

        damage = calculate_damage(attacker, defender, weapon)
        assert damage == 0  # Can't deal negative damage
```

#### React Tests
```typescript
// UnitCard.test.tsx
import { render, fireEvent } from '@testing-library/react';
import { UnitCard } from './UnitCard';
import { mockUnit } from '../utils/mockData';

describe('UnitCard', () => {
  it('renders unit information', () => {
    const { getByText } = render(
      <UnitCard
        unit={mockUnit}
        selected={false}
        onSelect={jest.fn()}
      />
    );

    expect(getByText(mockUnit.name)).toBeInTheDocument();
    expect(getByText(mockUnit.unitClass)).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = jest.fn();
    const { container } = render(
      <UnitCard
        unit={mockUnit}
        selected={false}
        onSelect={onSelect}
      />
    );

    fireEvent.click(container.firstChild);
    expect(onSelect).toHaveBeenCalledWith(mockUnit);
  });
});
```

## Pull Request Process

### Before Creating PR

1. **Run all tests**
   ```bash
   # Python
   python -m pytest

   # React
   cd fe-client && npm test
   ```

2. **Check code style**
   ```bash
   # Python
   black agent/
   flake8 agent/

   # TypeScript
   cd fe-client && npm run lint
   ```

3. **Update documentation**
   - Docstrings for new functions
   - Update ARCHITECTURE.md if needed
   - Add to CHANGELOG.md

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added for new functionality
- [ ] All tests passing

## Screenshots (if UI changes)
[Add screenshots here]

## Related Issues
Closes #(issue number)
```

### Code Review Process

1. **Automated checks**
   - CI/CD pipeline runs tests
   - Linting checks pass
   - Code coverage maintained

2. **Reviewer checklist**
   - Logic correctness
   - Performance impact
   - Security considerations
   - Code style consistency
   - Test coverage

3. **Addressing feedback**
   ```bash
   # Make requested changes
   git add .
   git commit -m "fix: address review feedback"
   git push origin feature/your-feature
   ```

## Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH
- Example: 1.2.3

### Creating a Release

1. **Create release branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/1.2.0
   ```

2. **Update version**
   - Update version in package.json
   - Update CHANGELOG.md
   - Update any version constants

3. **Final testing**
   - Run full test suite
   - Manual smoke testing
   - Performance validation

4. **Merge to main**
   ```bash
   # Create PR to main
   # After approval and merge
   git checkout main
   git pull origin main
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

5. **Merge back to develop**
   ```bash
   git checkout develop
   git merge main
   git push origin develop
   ```

## Getting Help

### Resources
- [Project Documentation](./ARCHITECTURE.md)
- [Fire Emblem Wiki](https://fireemblemwiki.org)
- [Discord Server](#) (Coming soon)

### Contact
- Open an issue for bugs
- Start a discussion for features
- Email: [maintainer@example.com](mailto:maintainer@example.com)

## Code of Conduct

### Our Standards
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the project
- Show empathy towards others

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or insulting comments
- Public or private harassment
- Publishing private information
- Unprofessional conduct

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.