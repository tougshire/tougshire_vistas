function hide_multiselect(multiSelect) {
	let textBox = document.createElement("input")
	textBox.dataset.multiselect=multiSelect.id
    textBox.id = 'ctl_multiselectdisplay_' + multiSelect.id
	textBox.addEventListener("click", function(e){
		e.preventDefault()
		show_multiselect(textBox)
	})
	textBox.addEventListener("focus", function(e){
		e.preventDefault()
		show_multiselect(textBox)
	})

    /*tp23bcc49 make the op box show multiselect on change*/
    /*ctl_filter__op__{{ field.name }}__{{ forloop.parentloop.counter0 }} */
    /*ctl_filter__value__{{ field.name }}__{{ forloop.parentloop.counter0 }}*/
    let optionSelectId = multiSelect.id.replace("value","op")
    let optionSelect = document.getElementById(optionSelectId)
	optionSelect.dataset.multiselect=multiSelect.id
	// optionSelect.addEventListener("click", function(e){
	// 	/*e.preventDefault()*/
	// 	show_multiselect(textBox)
	// })
	optionSelect.addEventListener("change", function(e){
		/*e.preventDefault()*/
		show_multiselect(textBox)
	})


    /* Show the values of selected inputs in a text box */
    let selected_qty = 0
	let selected_text = ''
	for(op=0; op < multiSelect.options.length; op++) {
		if(multiSelect.options[op].selected){
			selected_qty++
			if(selected_qty == 1 ) {
				selected_text = multiSelect.options[op].innerText
			} else if (selected_qty == 2 ) {
				selected_text = selected_text + ', ' + multiSelect.options[op].innerText
			} else if (selected_qty > 2 ) {
				selected_text = selected_text + ", ..."
				break
			}
		}
	}
	textBox.value = selected_text
	multiSelect.parentNode.insertBefore(textBox, multiSelect)
	multiSelect.dataset.displaystyle=multiSelect.style.display
	multiSelect.style.display = "none"
}

function show_multiselect(textBox) {
	let multiSelect = document.getElementById(textBox.dataset.multiselect)
	multiSelect.parentNode.insertBefore(textBox, multiSelect)
    multiSelect.style.position="absolute"
    multiSelect.style.zIndex=1

	multiSelect.style.display = multiSelect.dataset.displaystyle
    if(textBox === document.activeElement) {
        multiSelect.focus()
    }
	textBox.remove()
}

function hide_multiselects(container, target=null){
    multiSelects = container.querySelectorAll('select[multiple="MULTIPLE"]')
    for(multiSelect of multiSelects) {
        if(target !== null) {
            if(multiSelect.id != target.dataset.multiselect){
                if(multiSelect.id != target.id ) {
                    if(multiSelect.id != target.parentNode.id) {
                        if(multiSelect.style.display != 'none'){
                            hide_multiselect(multiSelect)
                        }
                    }
                }
            }
        } else {
            hide_multiselect(multiSelect)
        }
    }
}

function init_multiselect_container(container) {

	container.addEventListener("click", function(e) {
        hide_multiselects(container, e.target)
	})
	container.addEventListener("focusout", function(e) {
        if(e.target.getAttribute("multiple")) {
            hide_multiselects(container, container)
        }
	})

    hide_multiselects(container, container)

}
