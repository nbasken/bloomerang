    with col2:
        st.markdown("**👤 Parent 2 (Optional)**")
        
        if search_method == "By Name":
            person2_first = st.text_input(
                "First Name", 
                key="person2_first",
                on_change=auto_search_person_by_name,
                args=(2,),
                placeholder="Start typing to search automatically..."
            )
            person2_last = st.text_input(
                "Last Name", 
                key="person2_last",
                on_change=auto_search_person_by_name,
                args=(2,),
                placeholder="Start typing to search automatically..."
            )
        else:  # By Account Number
            person2_account = st.text_input(
                "Account Number", 
                key="person2_account",
                placeholder="Enter account number..."
            )
            # Don't show name fields when using account search
        
        person2_relationship = st.selectbox(
            "Relationship", 
            ["", "father", "mother", "husband", "wife","brother","sister"],
            key="person2_relationship",
            help="Leave blank if no specific relationship needed"
        )
