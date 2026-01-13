class SearchableSelect {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.selectId = wrapper.dataset.target;
        this.select = document.getElementById(this.selectId);
        
        if (!this.select) {
            console.error(`SearchableSelect: Could not find select element with id "${this.selectId}"`);
            return;
        }
        
        this.searchInput = wrapper.querySelector('.search-input');
        this.optionsList = wrapper.querySelector('.options-list');
        this.dropdownIcon = wrapper.querySelector('.dropdown-icon');
        
        this.options = [];
        this.selectedValue = null;
        this.isDisabled = false;
        
        this.init();
    }
    
    init() {
        // Check if select is disabled
        this.isDisabled = this.select.disabled;
        if (this.isDisabled) {
            this.searchInput.disabled = true;
            this.wrapper.classList.add('disabled');
            return;
        }
        
        // Parse options from select element
        this.parseOptions();
        
        // Set initial value if one is selected
        const selectedOption = Array.from(this.select.options).find(opt => opt.selected && opt.value);
        if (selectedOption) {
            this.selectedValue = selectedOption.value;
            this.searchInput.value = selectedOption.textContent.trim();
        }
        
        // Bind event listeners
        this.bindEvents();
        
        // Observe changes to the select element (for dynamic updates)
        this.observeSelectChanges();
    }
    
    parseOptions() {
        this.options = [];
        const selectOptions = this.select.querySelectorAll('option');
        
        selectOptions.forEach(option => {
            // Skip empty/placeholder options
            if (option.value && option.value !== '') {
                this.options.push({
                    value: option.value,
                    text: option.textContent.trim(),
                    disabled: option.hasAttribute('disabled') || option.disabled,
                    element: option,
                    searchText: option.textContent.trim().toLowerCase()
                });
            }
        });
    }
    
    bindEvents() {
        // Search input events
        this.searchInput.addEventListener('input', () => this.filterOptions());
        this.searchInput.addEventListener('focus', () => {
            // Show all options when focused if search is empty
            if (this.searchInput.value.trim() === '') {
                this.renderOptions(this.options);
            }
            this.showOptions();
        });
        this.searchInput.addEventListener('keydown', (e) => this.handleKeyboard(e));
        this.searchInput.addEventListener('blur', () => {
            // Delay to allow option click to register
            setTimeout(() => this.handleBlur(), 200);
        });
        
        // Dropdown icon click
        if (this.dropdownIcon) {
            this.dropdownIcon.addEventListener('mousedown', (e) => {
                e.preventDefault(); // Prevent input blur
                if (this.optionsList.classList.contains('show')) {
                    this.hideOptions();
                    this.searchInput.blur();
                } else {
                    // Show all options when dropdown icon is clicked
                    this.searchInput.value = '';
                    this.searchInput.focus();
                    this.renderOptions(this.options);
                    this.showOptions();
                }
            });
        }
        
        // Click outside to close
        document.addEventListener('click', (e) => {
            if (!this.wrapper.contains(e.target)) {
                this.hideOptions();
            }
        });
    }
    
    observeSelectChanges() {
        // Watch for programmatic changes to the select element
        const observer = new MutationObserver(() => {
            this.parseOptions();
            if (this.optionsList.classList.contains('show')) {
                this.filterOptions();
            }
        });
        
        observer.observe(this.select, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['disabled']
        });
        
        this.selectObserver = observer;
    }
    
    filterOptions() {
        const searchTerm = this.searchInput.value.toLowerCase().trim();
        
        let filtered;
        if (searchTerm === '') {
            filtered = this.options;
        } else {
            filtered = this.options.filter(opt => 
                opt.searchText.includes(searchTerm)
            );
        }
        
        this.renderOptions(filtered, searchTerm);
        this.showOptions();
    }
    
    renderOptions(options, searchTerm = '') {
        this.optionsList.innerHTML = '';
        
        if (options.length === 0) {
            const noResults = document.createElement('div');
            noResults.className = 'no-results';
            noResults.textContent = searchTerm ? 'No results found' : 'No options available';
            this.optionsList.appendChild(noResults);
            return;
        }
        
        options.forEach(option => {
            const optionDiv = document.createElement('div');
            optionDiv.className = 'option-item';
            optionDiv.textContent = option.text;
            optionDiv.dataset.value = option.value;
            
            if (option.disabled) {
                optionDiv.classList.add('disabled');
                optionDiv.title = 'This option is not available';
            } else {
                optionDiv.addEventListener('mousedown', (e) => {
                    e.preventDefault(); 
                    this.selectOption(option);
                });
                
                optionDiv.addEventListener('mouseenter', () => {
                    this.clearFocused();
                    optionDiv.classList.add('focused');
                });
            }
            
            if (option.value === this.selectedValue) {
                optionDiv.classList.add('selected');
            }
            
            this.optionsList.appendChild(optionDiv);
        });
    }
    
    selectOption(option) {
        if (option.disabled) return;
        
        this.selectedValue = option.value;
        this.searchInput.value = option.text;
        this.select.value = option.value;
        
        const changeEvent = new Event('change', { bubbles: true });
        this.select.dispatchEvent(changeEvent);
        
        this.hideOptions();
        this.searchInput.blur();
    }
    
    showOptions() {
        if (this.options.length > 0 && !this.isDisabled) {
            if (this.searchInput.value.trim() === '') {
                this.renderOptions(this.options);
            }
            this.optionsList.classList.add('show');
            this.wrapper.classList.add('open');
        }
    }
    
    hideOptions() {
        this.optionsList.classList.remove('show');
        this.wrapper.classList.remove('open');
    }
    
    handleBlur() {
        if (this.selectedValue) {
            const selectedOption = this.options.find(opt => opt.value === this.selectedValue);
            if (selectedOption) {
                this.searchInput.value = selectedOption.text;
            }
        } else {
            this.searchInput.value = '';
        }
        this.hideOptions();
    }
    
    handleKeyboard(e) {
        const items = Array.from(this.optionsList.querySelectorAll('.option-item:not(.disabled)'));
        if (items.length === 0) return;
        
        const currentFocus = this.optionsList.querySelector('.option-item.focused');
        let index = items.indexOf(currentFocus);
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (!this.optionsList.classList.contains('show')) {
                    this.showOptions();
                } else {
                    index = index < items.length - 1 ? index + 1 : 0;
                    this.focusOption(items[index]);
                }
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                if (!this.optionsList.classList.contains('show')) {
                    this.showOptions();
                } else {
                    index = index > 0 ? index - 1 : items.length - 1;
                    this.focusOption(items[index]);
                }
                break;
                
            case 'Enter':
                e.preventDefault();
                if (currentFocus) {
                    const value = currentFocus.dataset.value;
                    const option = this.options.find(opt => opt.value === value);
                    if (option && !option.disabled) {
                        this.selectOption(option);
                    }
                } else if (items.length === 1) {
                    // Auto-select if only one option
                    const value = items[0].dataset.value;
                    const option = this.options.find(opt => opt.value === value);
                    if (option && !option.disabled) {
                        this.selectOption(option);
                    }
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                this.hideOptions();
                this.searchInput.blur();
                break;
                
            case 'Tab':
                this.hideOptions();
                break;
        }
    }
    
    focusOption(item) {
        this.clearFocused();
        if (item) {
            item.classList.add('focused');
            item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }
    }
    
    clearFocused() {
        const items = this.optionsList.querySelectorAll('.option-item');
        items.forEach(i => i.classList.remove('focused'));
    }
    
    refresh() {
        this.parseOptions();
        if (this.optionsList.classList.contains('show')) {
            this.filterOptions();
        }
    }
    
    destroy() {
        if (this.selectObserver) {
            this.selectObserver.disconnect();
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSearchableSelects);
} else {
    initSearchableSelects();
}

function initSearchableSelects() {
    const wrappers = document.querySelectorAll('.searchable-select-wrapper');
    wrappers.forEach(wrapper => {
        if (!wrapper.searchableSelectInstance) {
            wrapper.searchableSelectInstance = new SearchableSelect(wrapper);
        }
    });
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchableSelect;
}
