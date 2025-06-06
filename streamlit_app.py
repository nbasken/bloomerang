import streamlit as st
import requests
from typing import Dict, Optional, Tuple, List

st.set_page_config(
    page_title="Bloomerang Household Manager",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# Authentification
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password in memory
        else:
            st.session_state["password_correct"] = False

    # First run - no password entered yet
    if "password_correct" not in st.session_state:
        st.markdown("# 🔐 Bloomerang Relationship Manager")
        st.markdown("---")
        st.info("This application is for authorized staff only. Please enter the password to continue.")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            help="Contact your administrator if you need the password"
        )
        st.markdown("---")
        st.markdown("*Authorized users only - Unauthorized access is prohibited*")
        return False
    
    # Password was incorrect
    elif not st.session_state["password_correct"]:
        st.markdown("# 🔐 Bloomerang Relationship Manager")
        st.markdown("---")
        st.error("❌ Incorrect password. Please try again.")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            help="Contact your administrator if you need the password"
        )
        st.markdown("---")
        st.markdown("*Authorized users only - Unauthorized access is prohibited*")
        return False
    
    # Password correct
    else:
        return True

def add_logout_button():
    """Add a logout button to the sidebar"""
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Logout", help="Clear session and return to login"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# =====================================================
# App Entry
if not check_password():
    st.stop()

# API Configuration
API_BASE_URL = "https://api.bloomerang.co/v2"
try:
    API_KEY = st.secrets["BLOOMERANG_API_KEY"]
except KeyError:
    st.error("❌ API configuration error. Please contact the administrator.")
    st.info("The application is not properly configured. Contact your system administrator.")
    st.stop()
HEADERS = {
    "Content-Type": "application/json",
    "X-API-KEY": API_KEY
}
add_logout_button()

RELATIONSHIP_ROLES = {
    'brother': 16,
    'co-worker': 17,
    'daughter': 18,
    'employee': 19,
    'employer': 20,
    'father': 21,
    'friend': 22,
    'husband': 23,
    'mother': 24,
    'partner': 25,
    'sister': 26,
    'son': 27,
    'wife': 28,
    'mom': 24,
    'dad': 21,
}

# =====================================================
# NEW FUNCTIONS FOR EXISTING HOUSEHOLD MANAGEMENT
# =====================================================

def get_constituent_by_id(constituent_id: int) -> Optional[Dict]:
    """Get full constituent details by ID with session caching"""
    if not constituent_id:
        return None
        
    cache_key = str(constituent_id)
    if cache_key in st.session_state.get('cached_constituents', {}):
        return st.session_state['cached_constituents'][cache_key]
    
    try:
        url = f"{API_BASE_URL}/constituent/{constituent_id}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            result = response.json()
            # Cache the result
            st.session_state['cached_constituents'][cache_key] = result
            return result
        return None
    except Exception as e:
        st.error(f"Error getting constituent details: {str(e)}")
        return None

def get_household_by_id(household_id: int) -> Optional[Dict]:
    """Get household details by ID with session caching"""
    if not household_id:
        return None
        
    # Check cache first
    cache_key = str(household_id)
    if cache_key in st.session_state.get('cached_households', {}):
        return st.session_state['cached_households'][cache_key]
    
    # If not cached, fetch from API
    try:
        url = f"{API_BASE_URL}/household/{household_id}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            result = response.json()
            # Cache the result
            st.session_state['cached_households'][cache_key] = result
            return result
        return None
    except Exception as e:
        st.error(f"Error getting household details: {str(e)}")
        return None


def check_existing_household(person_data: Dict) -> Optional[Dict]:
    """Check if a person is already in a household"""
    if not person_data:
        return None
    
    household_id = person_data.get("HouseholdId")
    if household_id and household_id > 0:
        return get_household_by_id(household_id)
    
    return None

def clear_caches():
    """Clear all session caches - useful for 'refresh' functionality"""
    st.session_state['cached_constituents'] = {}
    st.session_state['cached_households'] = {}
    st.session_state['cached_household_members'] = {}

# Find and REPLACE the entire get_household_members function:
def get_household_members(household_id: int) -> List[Dict]:
    """Get all members of a household with optimized caching"""
    if not household_id:
        return []
        
    # Check cache first
    cache_key = str(household_id)
    if cache_key in st.session_state.get('cached_household_members', {}):
        return st.session_state['cached_household_members'][cache_key]
    
    try:
        # Get household details (this will use caching too)
        household = get_household_by_id(household_id)
        if not household:
            return []
        
        members = []
        
        # Get head of household
        head_id = household.get("HeadId")
        if head_id:
            head_data = get_constituent_by_id(head_id)  # This will use caching too
            if head_data:
                head_data["_household_role"] = "Head"
                members.append(head_data)
        
        # Get other members (but NOT the head again)
        member_ids = household.get("MemberIds", [])
        for member_id in member_ids:
            # Skip if this member_id is the same as head_id
            if member_id == head_id:
                continue
                
            member_data = get_constituent_by_id(member_id)  # This will use caching too
            if member_data:
                member_data["_household_role"] = "Member"
                members.append(member_data)
        
        # Cache the result
        st.session_state['cached_household_members'][cache_key] = members
        return members
        
    except Exception as e:
        st.error(f"Error getting household members: {str(e)}")
        return []
    
def update_household_names(household_id: int, new_names: Dict) -> bool:
    """Update household names (for adding spouse scenarios)"""
    try:
        # Get current household data
        current_household = get_household_by_id(household_id)
        if not current_household:
            return False
        
        # Get current members
        current_members = get_household_members(household_id)
        
        # Prepare update payload with new names
        updated_members = []
        head_data = None
        
        for member in current_members:
            member_info = {
                "Id": member.get("Id"),
                "Type": "Individual",
                "Status": "Active",
                "FirstName": member.get("FirstName", ""),
                "LastName": member.get("LastName", "")
            }
            
            if member.get("_household_role") == "Head":
                head_data = member_info
            else:
                updated_members.append(member_info)
        
        update_payload = {
            "Id": household_id,
            "FullName": new_names.get("FullName"),
            "SortName": new_names.get("SortName"),
            "InformalName": new_names.get("InformalName"),
            "FormalName": new_names.get("FormalName"),
            "EnvelopeName": new_names.get("EnvelopeName"),
            "RecognitionName": new_names.get("RecognitionName"),
            "Head": head_data,
            "Members": updated_members
        }

        
        # Update household
        url = f"{API_BASE_URL}/household/{household_id}"
        response = requests.put(url, headers=HEADERS, json=update_payload)
        
        return response.status_code in [200, 201]
        
    except Exception as e:
        st.error(f"Error updating household names: {str(e)}")
        return False

# =====================================================
# YOUR EXISTING FUNCTIONS (UNCHANGED)
# =====================================================

def search_constituent_by_account_number(account_number: str) -> Optional[Dict]:
    """Search for a constituent by account number"""
    try:
        # Remove # if present
        account_num = account_number.replace("#", "").strip()
        
        url = f"{API_BASE_URL}/constituents/search"
        params = {
            "search": account_num,
            "type": "Individual",
            "take": 50  # Get more results to find exact match
        }
        
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            st.error(f"Error searching for account number {account_number}: {response.status_code}")
            return None
        
        data = response.json()
        results = data.get("Results", [])
        
        # Look for exact account number match
        for result in results:
            if str(result.get("AccountNumber", "")) == account_num:
                return result
        
        return None
        
    except Exception as e:
        st.error(f"Error searching for account number: {str(e)}")
        return None


def search_constituents(first_name: str, last_name: str) -> Optional[Dict]:
    """Search for a constituent by first and last name"""
    url = f"{API_BASE_URL}/constituents/search"
    params = {
        "search": f"{first_name} {last_name}",
        "type": "Individual"
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            st.error(f"Error searching for constituent {first_name} {last_name}: {response.status_code}")
            return None
        
        data = response.json()
        
        # Check if we found any results
        if data.get("ResultCount", 0) == 0:
            return None
        
        # Find the best match
        for result in data.get("Results", []):
            if (result.get("FirstName", "").lower() == first_name.lower() and 
                result.get("LastName", "").lower() == last_name.lower()):
                return result
        
        # If no exact match, return the first result
        return data.get("Results", [{}])[0]
    
    except Exception as e:
        st.error(f"Error searching for constituent: {str(e)}")
        return None

def check_for_duplicate_names(first_name: str, last_name: str) -> list:
    """Check if there are multiple people with the same name"""
    try:
        url = f"{API_BASE_URL}/constituents/search"
        params = {
            "search": f"{first_name} {last_name}",
            "type": "Individual",
            "take": 20
        }
        
        response = requests.get(url, headers=HEADERS, params=params)
        if response.status_code != 200:
            return []
        
        data = response.json()
        results = data.get("Results", [])
        
        # Filter for exact name matches
        exact_matches = []
        for result in results:
            if (result.get("FirstName", "").lower() == first_name.lower() and 
                result.get("LastName", "").lower() == last_name.lower()):
                exact_matches.append(result)
        
        return exact_matches
        
    except Exception as e:
        return []

# Replace the format_household_names_with_relationship function
# Find this function around line 200-400 and replace the entire function:

def format_household_names_with_relationship(first1: str, last1: str, first2: str, last2: str, 
                                           rel1: str = "", rel2: str = "", children: List[Dict] = None) -> Dict[str, str]:
    """Format household names according to the relationship type"""
    
    def is_parent_child_relationship(r1: str, r2: str) -> bool:
        parent_roles = ['mother', 'father', 'mom', 'dad']
        child_roles = ['daughter', 'son', 'child']
        r1_lower = r1.lower() if r1 else ""
        r2_lower = r2.lower() if r2 else ""
        return ((r1_lower in parent_roles and r2_lower in child_roles) or
                (r1_lower in child_roles and r2_lower in parent_roles))
    
    def is_spouse_relationship(r1: str, r2: str) -> bool:
        spouse_roles = ['husband', 'wife', 'spouse', 'partner']
        r1_lower = r1.lower() if r1 else ""
        r2_lower = r2.lower() if r2 else ""
        return r1_lower in spouse_roles and r2_lower in spouse_roles
    
    def is_unmarried_parents(r1: str, r2: str) -> bool:
        parent_roles = ['mother', 'father', 'mom', 'dad']
        r1_lower = r1.lower() if r1 else ""
        r2_lower = r2.lower() if r2 else ""
        return r1_lower in parent_roles and r2_lower in parent_roles and not is_spouse_relationship(r1, r2)
    
    def is_sibling_relationship(r1: str, r2: str) -> bool:
        sibling_roles = ['brother', 'sister']
        r1_lower = r1.lower() if r1 else ""
        r2_lower = r2.lower() if r2 else ""
        return r1_lower in sibling_roles and r2_lower in sibling_roles
    
    def is_single_parent(first2_param: str, last2_param: str, rel1_param: str, children_param: List[Dict]) -> bool:
        """Check if this is a single parent household"""
        parent_roles = ['mother', 'father', 'mom', 'dad']
        return (not first2_param or not last2_param) and rel1_param.lower() in parent_roles and children_param and len(children_param) > 0
    
    # PRIORITY CHECK: Single parent with children - use single parent format
    if is_single_parent(first2, last2, rel1, children):
        parent_title = "Ms." if rel1.lower() in ['mother', 'mom'] else "Mr."
        
        return {
            "FullName": f"The {last1} Family",
            "SortName": f"{last1}, {first1}",
            "InformalName": first1,
            "FormalName": f"{parent_title} {last1}",
            "EnvelopeName": f"{first1} {last1}",
            "RecognitionName": f"{parent_title} {first1} {last1}"
        }
    
    # Two parents with children - family household
    if children and len(children) > 0 and first2 and last2:
        # Married parents (husband/wife)
        if is_spouse_relationship(rel1, rel2):
            # Use husband's last name for family name, but check for different last names
            if last1.lower() == last2.lower():
                # Same last name - traditional married format
                family_last_name = last1
                return {
                    "FullName": f"The {first1} {family_last_name} Family",
                    "SortName": f"{family_last_name}, {first1} and {first2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. and Mrs. {family_last_name}",
                    "EnvelopeName": f"{first1} and {first2} {family_last_name}",
                    "RecognitionName": f"Mr. and Mrs. {first1} and {first2} {family_last_name}"
                }
            else:
                # Different last names - modern married format
                return {
                    "FullName": f"The {last1}/{last2} Family",
                    "SortName": f"{last1}, {first1} and {first2} {last2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. {last1} and Mrs. {last2}",
                    "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                    "RecognitionName": f"Mr. {first1} {last1} and Mrs. {first2} {last2}"
                }
        
        # Unmarried parents (father/mother)
        elif is_unmarried_parents(rel1, rel2):
            if last1.lower() == last2.lower():
                # Same last name - unmarried parents
                return {
                    "FullName": f"The {last1} Family",
                    "SortName": f"{last1}, {first1} and {first2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"The {last1} Family",
                    "EnvelopeName": f"{first1} and {first2} {last1}",
                    "RecognitionName": f"The {first1} and {first2} {last1} Family"
                }
            else:
                # Different last names - unmarried parents format
                parent1_title = "Mr." if rel1.lower() in ['father', 'dad'] else "Ms."
                parent2_title = "Mr." if rel2.lower() in ['father', 'dad'] else "Ms."
                return {
                    "FullName": f"The {last1}/{last2} Family",
                    "SortName": f"{last1}, {first1} and {first2} {last2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"{parent1_title} {last1} and {parent2_title} {last2}",
                    "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                    "RecognitionName": f"{parent1_title} {first1} {last1} and {parent2_title} {first2} {last2}"
                }
        
        # Default family format with children (when relationships aren't clearly defined)
        else:
            if last1.lower() == last2.lower():
                # Same last name - generic family format
                return {
                    "FullName": f"The {last1} Family",
                    "SortName": f"{last1}, {first1} and {first2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"The {last1} Family",
                    "EnvelopeName": f"{first1} and {first2} {last1}",
                    "RecognitionName": f"The {first1} and {first2} {last1} Family"
                }
            else:
                # Different last names - generic family format
                return {
                    "FullName": f"The {last1}/{last2} Family",
                    "SortName": f"{last1}, {first1} and {first2} {last2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"The {last1}/{last2} Family",
                    "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                    "RecognitionName": f"The {first1} {last1} and {first2} {last2} Family"
                }
    
    # Two adults, no children scenarios
    if first2 and last2 and (not children or len(children) == 0):
        # Parent-child relationship between adults - use single parent format
        if is_parent_child_relationship(rel1, rel2):
            parent_roles = ['mother', 'father', 'mom', 'dad']
            if rel1.lower() in parent_roles:
                parent_first, parent_last = first1, last1
                parent_title = "Ms." if rel1.lower() in ['mother', 'mom'] else "Mr."
            else:
                parent_first, parent_last = first2, last2
                parent_title = "Ms." if rel2.lower() in ['mother', 'mom'] else "Mr."
            
            return {
                "FullName": f"The {parent_last} Family",
                "SortName": f"{parent_last}, {parent_first}",
                "InformalName": parent_first,
                "FormalName": f"{parent_title} {parent_last}",
                "EnvelopeName": f"{parent_first} {parent_last}",
                "RecognitionName": f"{parent_title} {parent_first} {parent_last}"
            }
        
        # Sibling relationship with same last name
        elif is_sibling_relationship(rel1, rel2) and last1.lower() == last2.lower():
            return {
                "FullName": f"The {last1} Family",
                "SortName": f"{last1}, {first1} and {first2}",
                "InformalName": f"{first1} and {first2}",
                "FormalName": f"The {last1} Siblings",
                "EnvelopeName": f"{first1} and {first2} {last1}",
                "RecognitionName": f"{first1} and {first2} {last1}"
            }
        
        # Sibling relationship with different last names
        elif is_sibling_relationship(rel1, rel2) and last1.lower() != last2.lower():
            return {
                "FullName": f"The {last1}/{last2} Family",
                "SortName": f"{last1}, {first1} and {first2} {last2}",
                "InformalName": f"{first1} and {first2}",
                "FormalName": f"The {last1}/{last2} Siblings",
                "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                "RecognitionName": f"{first1} {last1} and {first2} {last2}"
            }
        
        # Spouse relationship - married couple
        elif is_spouse_relationship(rel1, rel2):
            if last1.lower() == last2.lower():
                # Same last name
                return {
                    "FullName": f"The {first1} {last1} Family",
                    "SortName": f"{last1}, {first1} and {first2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. and Mrs. {last1}",
                    "EnvelopeName": f"{first1} and {first2} {last1}",
                    "RecognitionName": f"Mr. and Mrs. {first1} and {first2} {last1}"
                }
            else:
                # Different last names
                return {
                    "FullName": f"The {last1}/{last2} Family",
                    "SortName": f"{last1}, {first1} and {first2} {last2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. {last1} and Mrs. {last2}",
                    "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                    "RecognitionName": f"Mr. {first1} {last1} and Mrs. {first2} {last2}"
                }
        
        # No specific relationship - generic couple format
        else:
            if last1.lower() == last2.lower():
                # Same last name
                return {
                    "FullName": f"The {first1} {last1} Family",
                    "SortName": f"{last1}, {first1} and {first2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. and Mrs. {last1}",
                    "EnvelopeName": f"{first1} and {first2} {last1}",
                    "RecognitionName": f"Mr. and Mrs. {first1} and {first2} {last1}"
                }
            else:
                # Different last names
                return {
                    "FullName": f"The {last1}/{last2} Family",
                    "SortName": f"{last1}, {first1} and {first2} {last2}",
                    "InformalName": f"{first1} and {first2}",
                    "FormalName": f"Mr. {last1} and Ms. {last2}",
                    "EnvelopeName": f"{first1} {last1} and {first2} {last2}",
                    "RecognitionName": f"Mr. {first1} {last1} and Ms. {first2} {last2}"
                }
    
    # Fallback for any remaining cases - shouldn't happen but good to have
    return {
        "FullName": f"The {last1} Family",
        "SortName": f"{last1}, {first1}",
        "InformalName": first1,
        "FormalName": f"The {last1} Family",
        "EnvelopeName": f"{first1} {last1}",
        "RecognitionName": f"The {first1} {last1} Family"
    }

def get_existing_relationships(person_id: int) -> List[Dict]:
    """Get all existing relationships for a person"""
    try:
        url = f"{API_BASE_URL}/constituent/{person_id}/relationships"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        return []

def get_parent_role_from_existing_relationships(member_id: int) -> str:
    """Get parent role from existing relationships, return None if not found"""
    try:
        relationships = get_existing_relationships(member_id)
        
        for rel in relationships:
            # Make sure rel is a dictionary, not a string
            if not isinstance(rel, dict):
                continue
                
            # Check if this person is AccountId1 or AccountId2
            if rel.get('AccountId1') == member_id:
                role = rel.get('Role1', '')
                if isinstance(role, str):
                    role = role.lower()
                else:
                    continue
            elif rel.get('AccountId2') == member_id:
                role = rel.get('Role2', '')
                if isinstance(role, str):
                    role = role.lower()
                else:
                    continue
            else:
                continue
                
            # If they're already a parent in any relationship, use that role
            if role in ['mother', 'father']:
                return role
        
        return None  # No existing parent relationship found
        
    except Exception as e:
        st.error(f"Error in relationship detection: {str(e)}")
        return None

   
def should_be_first(relationship: str) -> bool:
    """Determine if a relationship should be first (husband/parent)"""
    rel = relationship.lower().strip()
    return rel in ['husband', 'father', 'mother', 'dad', 'mom']

def get_sibling_relationship(child1_rel: str, child2_rel: str) -> Tuple[str, str]:
    """Determine sibling relationships based on child genders"""
    rel1_lower = child1_rel.lower()
    rel2_lower = child2_rel.lower()
    
    # Map child relationships to genders
    if rel1_lower == 'daughter':
        gender1 = 'female'
    elif rel1_lower == 'son':
        gender1 = 'male'
    else:
        gender1 = 'unknown'
    
    if rel2_lower == 'daughter':
        gender2 = 'female'
    elif rel2_lower == 'son':
        gender2 = 'male'
    else:
        gender2 = 'unknown'
    
    # Determine sibling relationships
    if gender1 == 'female' and gender2 == 'female':
        return ('sister', 'sister')
    elif gender1 == 'male' and gender2 == 'male':
        return ('brother', 'brother')
    elif gender1 == 'female' and gender2 == 'male':
        return ('sister', 'brother')
    elif gender1 == 'male' and gender2 == 'female':
        return ('brother', 'sister')
    else:
        return ('sibling', 'sibling')  # fallback

def get_parent_relationship_from_child(parent_rel: str, child_rel: str) -> str:
    """Convert parent relationship to appropriate relationship with child"""
    parent_lower = parent_rel.lower()
    
    if parent_lower in ['husband', 'father', 'dad']:
        return 'father'
    elif parent_lower in ['wife', 'mother', 'mom']:
        return 'mother'
    else:
        return parent_rel  # fallback

def create_relationship(person1_id: int, person2_id: int, rel1: str, rel2: str) -> bool:
    """Create a relationship between two constituents"""
    try:
        role1_id = RELATIONSHIP_ROLES.get(rel1.lower())
        role2_id = RELATIONSHIP_ROLES.get(rel2.lower())
        
        if not role1_id or not role2_id:
            st.warning(f"Unknown relationship roles: {rel1}, {rel2}")
            return False
        
        rel_payload = {
            "AccountId1": person1_id,
            "AccountId2": person2_id,
            "RelationshipRoleId1": role1_id,
            "RelationshipRoleId2": role2_id
        }
        
        rel_url = f"{API_BASE_URL}/relationship"
        rel_response = requests.post(rel_url, headers=HEADERS, json=rel_payload)
        
        if rel_response.status_code not in [200, 201]:
            # Check if it's a duplicate relationship error (often returns 400)
            if rel_response.status_code == 400:
                st.info(f"Relationship between accounts may already exist")
                return True  # Consider this a success since the relationship exists
            else:
                st.warning(f"Relationship creation failed: {rel_response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        st.warning(f"Error creating relationship: {str(e)}")
        return False

def create_household_with_children(people_data: List[Dict], household_names: Dict, 
                                 relationships: List[Tuple[int, int, str, str]]) -> Optional[Dict]:
    """Create household with multiple people and relationships"""
    try:
        # Prepare all constituent data
        def prepare_constituent_data_simple(constituent: Dict) -> Dict:
            """Simple version for new household creation"""
            base_data = {
                "Type": "Individual",
                "Status": "Active",
                "FirstName": constituent.get("FirstName", ""),
                "LastName": constituent.get("LastName", "")
            }
            
            # Only include Id if the constituent already exists
            if constituent.get("Id") and constituent.get("Id") > 0:
                base_data["Id"] = constituent.get("Id")
            
            # Add basic fields if they exist
            for field in ["MiddleName", "Gender", "Birthdate"]:
                if constituent.get(field):
                    base_data[field] = constituent.get(field)
            
            return base_data
        
        head_data = prepare_constituent_data_simple(people_data[0])
        members_data = [prepare_constituent_data_simple(person) for person in people_data[1:]]
        
        # Create payload
        payload = {
            **household_names,
            "Head": head_data,
            "Members": members_data
        }
        
        # Create household
        url = f"{API_BASE_URL}/household"
        response = requests.post(url, headers=HEADERS, json=payload)
        
        if response.status_code not in [200, 201]:
            st.error(f"Error creating household: {response.status_code}")
            st.error(response.text)
            return None
        
        household_data = response.json()
        
        # Create all relationships
        successful_relationships = 0
        total_relationships = len(relationships)
        
        if relationships:
            st.info(f"Creating {total_relationships} relationships...")
            
            for person1_idx, person2_idx, rel1, rel2 in relationships:
                person1_id = people_data[person1_idx].get("Id")
                person2_id = people_data[person2_idx].get("Id")
                
                if person1_id and person2_id:
                    if create_relationship(person1_id, person2_id, rel1, rel2):
                        successful_relationships += 1
                        st.success(f"✅ Created: {people_data[person1_idx]['FirstName']} ({rel1}) ↔ {people_data[person2_idx]['FirstName']} ({rel2})")
                    else:
                        st.warning(f"❌ Failed: {people_data[person1_idx]['FirstName']} ({rel1}) ↔ {people_data[person2_idx]['FirstName']} ({rel2})")
        
        if total_relationships > 0:
            st.info(f"Relationships created: {successful_relationships}/{total_relationships}")
        
        return household_data
        
    except Exception as e:
        st.error(f"Error creating household: {str(e)}")
        return None

# =====================================================
# INTERFACE FUNCTIONS
# =====================================================

def create_new_household_interface():
    """Interface for creating new households - your existing functionality"""
    
    # Initialize session state for children
    if 'new_children' not in st.session_state:
        st.session_state['new_children'] = []
    
    # Sidebar content moved to main area
    st.markdown("### 📖 How to Use")
    with st.expander("Click for instructions"):
        st.markdown("""
        1. **Enter names** for both parents
        2. **Select relationships** (husband/wife or father/mother)
        3. **Add children** if needed (use Add Child button)
        4. **Preview** the household naming
        5. **Edit names** if needed (check the edit box)
        6. **Create** the household with all relationships
        
        The app will:
        - Search for existing constituents
        - Create new ones if needed
        - Apply proper naming conventions
        - Create all family relationships automatically
        """)
    
    # Input method selection
    st.markdown("### 🔍 Search Method")
    search_method = st.radio(
        "How would you like to identify people?",
        ["By Name", "By Account Number"],
        help="Names work for most cases, but Account Numbers are unique if there are duplicate names",
        key="new_search_method"
    )
    
    # Main form for parents
    col1, col2 = st.columns(2)
    
    if search_method == "By Name":
        with col1:
            st.markdown("### 👤 Person 1 (Parent)")
            first1 = st.text_input("First Name", key="new_first1", placeholder="John")
            last1 = st.text_input("Last Name", key="new_last1", placeholder="Smith")
            rel1 = st.selectbox("Relationship", 
                               options=["", "husband", "father", "mother", "wife"], 
                               key="new_rel1",
                               help="Select parent/spouse role")
        
        with col2:
            st.markdown("### 👤 Person 2 (Parent)")
            first2 = st.text_input("First Name", key="new_first2", placeholder="Jane")
            last2 = st.text_input("Last Name", key="new_last2", placeholder="Smith")
            rel2 = st.selectbox("Relationship", 
                               options=["", "wife", "mother", "father", "husband"], 
                               key="new_rel2",
                               help="Select parent/spouse role")
    
    else:  # By Account Number
        with col1:
            st.markdown("### 👤 Person 1 (Parent)")
            account1 = st.text_input("Account Number", key="new_account1", placeholder="7722 or #7722")
            rel1 = st.selectbox("Relationship", 
                               options=["", "husband", "father", "mother", "wife"], 
                               key="new_rel1_acc",
                               help="Select parent/spouse role")
            first1 = last1 = ""
        
        with col2:
            st.markdown("### 👤 Person 2 (Parent)")
            account2 = st.text_input("Account Number", key="new_account2", placeholder="7723 or #7723")
            rel2 = st.selectbox("Relationship", 
                               options=["", "wife", "mother", "father", "husband"], 
                               key="new_rel2_acc",
                               help="Select parent/spouse role")
            first2 = last2 = ""

        # Lookup names for account numbers
        if search_method == "By Account Number":
            if account1:
                with st.spinner("Looking up account information..."):
                    person1_data = search_constituent_by_account_number(account1)
                    
                    if person1_data:
                        first1 = person1_data.get("FirstName", "")
                        last1 = person1_data.get("LastName", "")
                        st.success(f"✅ Found: {first1} {last1} (Account #{person1_data.get('AccountNumber')})")
                    else:
                        st.error(f"❌ Account number {account1} not found")
            
            # UPDATED: Only look up account2 if it has content AND is different from account1
            if account2 and account2.strip() and account2.strip() != account1.strip():
                with st.spinner("Looking up account information..."):
                    person2_data = search_constituent_by_account_number(account2)
                    
                    if person2_data:
                        first2 = person2_data.get("FirstName", "")
                        last2 = person2_data.get("LastName", "")
                        st.success(f"✅ Found: {first2} {last2} (Account #{person2_data.get('AccountNumber')})")
                    else:
                        st.error(f"❌ Account number {account2} not found")
            else:
                # Clear person2 data if account2 is empty
                first2 = ""
                last2 = ""
    # Children section
    st.markdown("---")
    st.markdown("### 👶 Children (Optional)")
    
    col_add, col_clear = st.columns([1, 4])
    with col_add:
        if st.button("➕ Add Child", type="secondary", key="new_add_child"):
            st.session_state['new_children'].append({
                'first_name': '',
                'last_name': '',
                'relationship': 'daughter',
                'account_number': '' if search_method == "By Account Number" else None
            })
            st.rerun()
    
    with col_clear:
        if len(st.session_state['new_children']) > 0 and st.button("🗑️ Clear All Children", key="new_clear_children"):
            st.session_state['new_children'] = []
            st.rerun()
    
    # Display children inputs
    for i, child in enumerate(st.session_state['new_children']):
        st.markdown(f"#### 👶 Child {i+1}")
        col1, col2, col3, col4 = st.columns([3, 3, 2, 1])
        
        if search_method == "By Name":
            with col1:
                child['first_name'] = st.text_input(
                    f"First Name", 
                    value=child['first_name'],
                    key=f"new_child_first_{i}",
                    placeholder="Emma"
                )
            with col2:
                child['last_name'] = st.text_input(
                    f"Last Name", 
                    value=child['last_name'],
                    key=f"new_child_last_{i}",
                    placeholder="Smith"
                )
        else:  # By Account Number
            with col1:
                child['account_number'] = st.text_input(
                    f"Account Number", 
                    value=child['account_number'],
                    key=f"new_child_account_{i}",
                    placeholder="7724 or #7724"
                )
            with col2:
                # Show looked up name if account number provided
                if child['account_number']:
                    child_data = search_constituent_by_account_number(child['account_number'])
                    if child_data:
                        child['first_name'] = child_data.get("FirstName", "")
                        child['last_name'] = child_data.get("LastName", "")
                        st.text(f"Name: {child['first_name']} {child['last_name']}")
                    else:
                        st.text("Name: Not found")
                        child['first_name'] = child['last_name'] = ""
                else:
                    st.text("Name: Enter account number")
        
        with col3:
            child['relationship'] = st.selectbox(
                f"Relationship",
                options=["daughter", "son"],
                index=0 if child['relationship'] == 'daughter' else 1,
                key=f"new_child_rel_{i}"
            )
        
        with col4:
            if st.button("❌", key=f"new_remove_child_{i}", help="Remove this child"):
                st.session_state['new_children'].pop(i)
                st.rerun()
        
        # Update the session state
        st.session_state['new_children'][i] = child
    
    # Preview section
    has_person1 = first1 and last1
    has_person2 = first2 and last2

    # For account number method, also check if account numbers are actually filled
    if search_method == "By Account Number":
        has_person1 = account1 and account1.strip() and first1 and last1
        has_person2 = (account2 and account2.strip() and 
                      account2.strip() != account1.strip() and 
                      first2 and last2)

    
    if has_person1 and (has_person2 or len(st.session_state.get('new_children', [])) > 0):
        st.markdown("---")
        st.markdown("### 👀 Preview")
        
        # Determine proper order for parents
        ordered_first1, ordered_last1, ordered_rel1 = first1, last1, rel1
        ordered_first2, ordered_last2, ordered_rel2 = first2, last2, rel2
        
        # Only reorder if we have both parents
        if has_person2 and rel1 and rel2 and should_be_first(rel2) and not should_be_first(rel1):
            ordered_first1, ordered_last1, ordered_rel1 = first2, last2, rel2
            ordered_first2, ordered_last2, ordered_rel2 = first1, last1, rel1
            st.info("💡 Order adjusted: putting husband/father first")
        
        # Collect all valid children
        valid_children = []
        for child in st.session_state['new_children']:
            if search_method == "By Name":
                if child['first_name'] and child['last_name']:
                    valid_children.append(child)
            else:
                if child['account_number'] and child['first_name'] and child['last_name']:
                    valid_children.append(child)
        
        # Generate household names
        household_names = format_household_names_with_relationship(
            ordered_first1, ordered_last1, 
            ordered_first2 if has_person2 else "", ordered_last2 if has_person2 else "",
            ordered_rel1, ordered_rel2 if has_person2 else "", valid_children
        )
        
        # Display preview with edit option
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Family Members (in order):**")
            st.text(f"Head: {ordered_first1} {ordered_last1}")
            if ordered_rel1:
                st.text(f"   Role: {ordered_rel1}")
            
            if has_person2:
                st.text(f"Member: {ordered_first2} {ordered_last2}")
                if ordered_rel2:
                    st.text(f"   Role: {ordered_rel2}")
            
            for i, child in enumerate(valid_children):
                st.text(f"Member: {child['first_name']} {child['last_name']}")
                st.text(f"   Role: {child['relationship']}")
        
        with col2:
            # Toggle for editing
            edit_mode = st.checkbox("✏️ Edit household names", help="Check this to customize the household naming", key="new_edit_mode")
        
        # Editable household names section
        if edit_mode:
            st.markdown("### ✏️ **Edit Household Names**")
            st.info("💡 Modify any of the household names below for edge cases or special requirements")
            
            col1, col2 = st.columns(2)
            
            with col1:
                edited_full_name = st.text_input(
                    "Full Name", 
                    value=household_names["FullName"],
                    help="Main household name",
                    key="new_edit_full"
                )
                edited_sort_name = st.text_input(
                    "Sort Name", 
                    value=household_names["SortName"],
                    help="Name used for sorting/searching",
                    key="new_edit_sort"
                )
                edited_informal_name = st.text_input(
                    "Informal Name", 
                    value=household_names["InformalName"],
                    help="Casual/friendly name",
                    key="new_edit_informal"
                )
            
            with col2:
                edited_formal_name = st.text_input(
                    "Formal Name", 
                    value=household_names["FormalName"],
                    help="Formal address name",
                    key="new_edit_formal"
                )
                edited_envelope_name = st.text_input(
                    "Envelope Name", 
                    value=household_names["EnvelopeName"],
                    help="Name for mailing envelopes",
                    key="new_edit_envelope"
                )
                edited_recognition_name = st.text_input(
                    "Recognition Name", 
                    value=household_names["RecognitionName"],
                    help="Name for recognition/awards",
                    key="new_edit_recognition"
                )
            
            # Update household_names with edited values
            household_names = {
                "FullName": edited_full_name,
                "SortName": edited_sort_name,
                "InformalName": edited_informal_name,
                "FormalName": edited_formal_name,
                "EnvelopeName": edited_envelope_name,
                "RecognitionName": edited_recognition_name
            }
            
            # Show warning if names were changed
            original_names = format_household_names_with_relationship(
                ordered_first1, ordered_last1, 
                ordered_first2 if has_person2 else "", ordered_last2 if has_person2 else "",
                ordered_rel1, ordered_rel2 if has_person2 else "", valid_children
            )
            
            changes_made = any(household_names[key] != original_names[key] for key in household_names.keys())
            if changes_made:
                st.warning("⚠️ You have customized the household names. The edited names will be used.")
        
        else:
            st.markdown("**Household Names:**")
            for key, value in household_names.items():
                st.text(f"{key}: {value}")
        
        # Show relationship preview
        if (ordered_rel1 or ordered_rel2) and (has_person2 or valid_children):
            st.markdown("**Relationships that will be created:**")
            
            # Parent relationships (only if both parents exist)
            if has_person2 and ordered_rel1 and ordered_rel2:
                parent_rel1 = ordered_rel1
                parent_rel2 = ordered_rel2
                if parent_rel1 in ['husband', 'wife'] and parent_rel2 in ['husband', 'wife']:
                    st.text(f"• {ordered_first1} ({parent_rel1}) ↔ {ordered_first2} ({parent_rel2})")
                elif parent_rel1 in ['father', 'mother'] and parent_rel2 in ['father', 'mother']:
                    st.text(f"• {ordered_first1} ({parent_rel1}) and {ordered_first2} ({parent_rel2}) - unmarried parents")
            
            # Parent-child relationships
            for child in valid_children:
                if ordered_rel1:
                    parent1_to_child = get_parent_relationship_from_child(ordered_rel1, child['relationship'])
                    st.text(f"• {ordered_first1} ({parent1_to_child}) ↔ {child['first_name']} ({child['relationship']})")
                
                if has_person2 and ordered_rel2:
                    parent2_to_child = get_parent_relationship_from_child(ordered_rel2, child['relationship'])
                    st.text(f"• {ordered_first2} ({parent2_to_child}) ↔ {child['first_name']} ({child['relationship']})")
            
            # Sibling relationships
            for i in range(len(valid_children)):
                for j in range(i + 1, len(valid_children)):
                    child1 = valid_children[i]
                    child2 = valid_children[j]
                    sib_rel1, sib_rel2 = get_sibling_relationship(child1['relationship'], child2['relationship'])
                    st.text(f"• {child1['first_name']} ({sib_rel1}) ↔ {child2['first_name']} ({sib_rel2})")
        
        # Store the final data in session state for use in creation
        st.session_state['new_final_household_names'] = household_names
        st.session_state['new_final_ordered_people'] = {
            'person1': {'first': ordered_first1, 'last': ordered_last1, 'rel': ordered_rel1},
            'person2': {'first': ordered_first2, 'last': ordered_last2, 'rel': ordered_rel2}
        }
        st.session_state['new_final_valid_children'] = valid_children
    
    # Create household button
    st.markdown("---")
    
    # Check if we have the required data
    has_required_data = (has_person1 and 
                        'new_final_household_names' in st.session_state and 
                        'new_final_ordered_people' in st.session_state and
                        (has_person2 or len(st.session_state.get('new_final_valid_children', [])) > 0))
    
    if st.button("🚀 Create Household", type="primary", disabled=not has_required_data, key="new_create_household"):
        with st.spinner("Creating household with all family members..."):
            # Get the data from session state
            household_names = st.session_state['new_final_household_names']
            ordered_people = st.session_state['new_final_ordered_people']
            valid_children = st.session_state.get('new_final_valid_children', [])
            
            final_first1 = ordered_people['person1']['first']
            final_last1 = ordered_people['person1']['last']
            final_rel1 = ordered_people['person1']['rel']
            final_first2 = ordered_people['person2']['first']
            final_last2 = ordered_people['person2']['last']
            final_rel2 = ordered_people['person2']['rel']
            
            # Search for all constituents
            all_people_data = []
            all_relationships = []
            
            # Search for parents
            if search_method == "By Name":
                # Handle duplicates for parent 1
                st.info(f"🔍 Searching for {final_first1} {final_last1}...")
                duplicates1 = check_for_duplicate_names(final_first1, final_last1)
                
                if len(duplicates1) > 1:
                    st.warning(f"⚠️ Found {len(duplicates1)} people named {final_first1} {final_last1}")
                    # For now, take the first match - in a real app, you'd want user selection
                    person1 = duplicates1[0]
                    st.info(f"Selected: Account #{person1.get('AccountNumber')}")
                else:
                    person1 = search_constituents(final_first1, final_last1)
                
                # Handle duplicates for parent 2 (only if person 2 exists)
                if has_person2 and final_first2 and final_last2:
                    st.info(f"🔍 Searching for {final_first2} {final_last2}...")
                    duplicates2 = check_for_duplicate_names(final_first2, final_last2)
                    
                    if len(duplicates2) > 1:
                        st.warning(f"⚠️ Found {len(duplicates2)} people named {final_first2} {final_last2}")
                        person2 = duplicates2[0]
                        st.info(f"Selected: Account #{person2.get('AccountNumber')}")
                    else:
                        person2 = search_constituents(final_first2, final_last2)
                else:
                    person2 = None
            
            else:  # By Account Number
                st.info(f"🔍 Looking up account #{account1}...")
                person1 = search_constituent_by_account_number(account1)
                
                if has_person2 and account2 and account2.strip():
                    st.info(f"🔍 Looking up account #{account2}...")
                    person2 = search_constituent_by_account_number(account2)
                else:
                    person2 = None
            
            # Handle missing parents
            if not person1:
                st.warning(f"⚠️ {final_first1} {final_last1} not found - will create new constituent")
                person1 = {
                    "FirstName": final_first1,
                    "LastName": final_last1,
                    "Type": "Individual",
                    "Status": "Active"
                }
            else:
                st.success(f"✅ Found {final_first1} {final_last1} (ID: {person1.get('Id')})")
            
            if has_person2 and final_first2 and final_last2:
                if not person2:
                    st.warning(f"⚠️ {final_first2} {final_last2} not found - will create new constituent")
                    person2 = {
                        "FirstName": final_first2,
                        "LastName": final_last2,
                        "Type": "Individual",
                        "Status": "Active"
                    }
                else:
                    st.success(f"✅ Found {final_first2} {final_last2} (ID: {person2.get('Id')})")
            
            # Add parents to people data
            all_people_data.append(person1)  # Head (index 0)
            if has_person2:
                all_people_data.append(person2)  # Member (index 1)
            
            # Search for children
            children_data = []
            for i, child in enumerate(valid_children):
                if search_method == "By Name":
                    st.info(f"🔍 Searching for child {child['first_name']} {child['last_name']}...")
                    child_person = search_constituents(child['first_name'], child['last_name'])
                else:
                    st.info(f"🔍 Looking up child account #{child['account_number']}...")
                    child_person = search_constituent_by_account_number(child['account_number'])
                
                if not child_person:
                    st.warning(f"⚠️ {child['first_name']} {child['last_name']} not found - will create new constituent")
                    child_person = {
                        "FirstName": child['first_name'],
                        "LastName": child['last_name'],
                        "Type": "Individual",
                        "Status": "Active"
                    }
                else:
                    st.success(f"✅ Found {child['first_name']} {child['last_name']} (ID: {child_person.get('Id')})")
                
                children_data.append(child_person)
                # Children start at index 1 (if no second parent) or 2 (if two parents)
                child_index = len(all_people_data)
                all_people_data.append(child_person)
            
            # Build relationships
            # Parent relationships (if both have relationship roles and both exist)
            if person2 and final_rel1 and final_rel2:
                # Check if it's a married couple vs unmarried parents
                if final_rel1 in ['husband', 'wife'] and final_rel2 in ['husband', 'wife']:
                    all_relationships.append((0, 1, final_rel1, final_rel2))
                # For unmarried parents (father/mother), we don't create a relationship between them
            
            # Parent-child relationships
            first_child_index = 2 if person2 else 1
            for i, child in enumerate(valid_children):
                child_index = first_child_index + i
                
                # Parent 1 to child
                if final_rel1:
                    parent1_to_child = get_parent_relationship_from_child(final_rel1, child['relationship'])
                    all_relationships.append((0, child_index, parent1_to_child, child['relationship']))
                
                # Parent 2 to child (only if parent 2 exists)
                if person2 and final_rel2:
                    parent2_to_child = get_parent_relationship_from_child(final_rel2, child['relationship'])
                    all_relationships.append((1, child_index, parent2_to_child, child['relationship']))
            
            # Sibling relationships
            for i in range(len(valid_children)):
                for j in range(i + 1, len(valid_children)):
                    child1_index = first_child_index + i
                    child2_index = first_child_index + j
                    sib_rel1, sib_rel2 = get_sibling_relationship(
                        valid_children[i]['relationship'], 
                        valid_children[j]['relationship']
                    )
                    all_relationships.append((child1_index, child2_index, sib_rel1, sib_rel2))
            
            # Create household with all members and relationships
            st.info("🏠 Creating household with all family members...")
            
            household_result = create_household_with_children(
                all_people_data, household_names, all_relationships
            )
            
            if household_result:
                st.success("🎉 Household created successfully!")
                
                # Display results
                st.markdown("### ✅ Family Household Created")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Household Details:**")
                    st.text(f"ID: {household_result.get('Id', 'N/A')}")
                    st.text(f"Name: {household_result.get('FullName', 'N/A')}")
                    
                    if household_result.get('FullName'):
                        st.markdown("**All Names:**")
                        name_fields = ['FullName', 'SortName', 'InformalName', 'FormalName', 'EnvelopeName', 'RecognitionName']
                        for field in name_fields:
                            if household_result.get(field):
                                st.text(f"{field}: {household_result[field]}")
                
                with col2:
                    st.markdown("**Family Members:**")
                    st.text(f"Head: {final_first1} {final_last1} ({final_rel1})")
                    if person1.get('Id'):
                        st.text(f"  ID: {person1['Id']}")
                    
                    if person2:
                        st.text(f"Member: {final_first2} {final_last2} ({final_rel2})")
                        if person2.get('Id'):
                            st.text(f"  ID: {person2['Id']}")
                    
                    for i, child in enumerate(valid_children):
                        st.text(f"Member: {child['first_name']} {child['last_name']} ({child['relationship']})")
                        if children_data[i].get('Id'):
                            st.text(f"  ID: {children_data[i]['Id']}")
                
                # Show relationship summary
                if all_relationships:
                    st.markdown("**✅ Relationships Created:**")
                    relationship_text = []
                    for person1_idx, person2_idx, rel1, rel2 in all_relationships:
                        person1_name = all_people_data[person1_idx]['FirstName']
                        person2_name = all_people_data[person2_idx]['FirstName']
                        relationship_text.append(f"• {person1_name} ({rel1}) ↔ {person2_name} ({rel2})")
                    
                    for rel_text in relationship_text:
                        st.text(rel_text)
                
                # Show equivalent command for reference
                with st.expander("📋 Equivalent Command Line"):
                    if person2:
                        command = f"python3 bloom_house.py --names \"{final_first1},{final_last1},{final_first2},{final_last2}"
                        if final_rel1 and final_rel2:
                            command += f",{final_rel1},{final_rel2}"
                        command += "\""
                    else:
                        command = f"python3 bloom_house.py --names \"{final_first1},{final_last1}"
                        if final_rel1:
                            command += f",,{final_rel1}"
                        command += "\""
                    
                    st.code(command)
                    if valid_children:
                        st.info("Note: Command line version doesn't support children yet.")

def on_relationship_change():
    """Callback function when relationship dropdowns change"""
    if 'parent_roles' not in st.session_state:
        st.session_state['parent_roles'] = {}
    
    # Get current selections
    parent_roles = st.session_state.get('parent_roles', {})
    
    # Check what types of relationships we have
    has_parent = any(role in ['father', 'mother'] for role in parent_roles.values())
    has_sibling = any(role in ['brother', 'sister'] for role in parent_roles.values())
    
    # Get the original relationship
    original_relationship = st.session_state.get('original_new_relationship', 'daughter')
    
    # Auto-adjust based on selections
    if has_sibling and not has_parent:
        # If someone is sibling, new person should be sibling too
        if original_relationship == 'daughter':
            st.session_state['adjusted_new_relationship'] = 'sister'
        elif original_relationship == 'son':
            st.session_state['adjusted_new_relationship'] = 'brother'
        else:
            st.session_state['adjusted_new_relationship'] = original_relationship
    elif has_parent:
        # If someone is parent, new person should be child
        if original_relationship in ['brother', 'sister']:
            if original_relationship == 'sister':
                st.session_state['adjusted_new_relationship'] = 'daughter'
            elif original_relationship == 'brother':
                st.session_state['adjusted_new_relationship'] = 'son'
            else:
                st.session_state['adjusted_new_relationship'] = original_relationship
        else:
            st.session_state['adjusted_new_relationship'] = original_relationship
    else:
        # No clear pattern, keep original
        st.session_state['adjusted_new_relationship'] = original_relationship              

def auto_search_existing_person_by_name():
    """Auto-search callback for existing person by name"""
    existing_first = st.session_state.get('existing_first', '').strip()
    existing_last = st.session_state.get('existing_last', '').strip()
    
    if existing_first and existing_last:
        # Search without spinner to avoid tab switching
        existing_person = search_constituents(existing_first, existing_last)
        if existing_person:
            st.session_state['existing_person'] = existing_person
            st.session_state['existing_household'] = check_existing_household(existing_person)
            if st.session_state['existing_household']:
                st.session_state['household_members'] = get_household_members(st.session_state['existing_household']['Id'])
        else:
            st.session_state['existing_person'] = None
            st.session_state['existing_household'] = None
            st.session_state['household_members'] = []

def auto_search_existing_person_by_account():
    """Auto-search callback for existing person by account number"""
    existing_account = st.session_state.get('existing_account', '').strip()
    
    if existing_account:
        # Search without spinner to avoid tab switching
        existing_person = search_constituent_by_account_number(existing_account)
        if existing_person:
            st.session_state['existing_person'] = existing_person
            st.session_state['existing_household'] = check_existing_household(existing_person)
            if st.session_state['existing_household']:
                st.session_state['household_members'] = get_household_members(st.session_state['existing_household']['Id'])
        else:
            st.session_state['existing_person'] = None
            st.session_state['existing_household'] = None
            st.session_state['household_members'] = []

def auto_search_new_person_by_name():
    """Auto-search callback for new person by name"""
    new_first = st.session_state.get('new_first', '').strip()
    new_last = st.session_state.get('new_last', '').strip()
    
    if new_first and new_last:
        # Search without spinner to avoid tab switching
        new_person = search_constituents(new_first, new_last)
        st.session_state['new_person_data'] = new_person
    else:
        st.session_state['new_person_data'] = None

def auto_search_new_person_by_account():
    """Auto-search callback for new person by account number"""
    new_account = st.session_state.get('new_account', '').strip()
    
    if new_account:
        # Search without spinner to avoid tab switching
        new_person = search_constituent_by_account_number(new_account)
        st.session_state['new_person_data'] = new_person
    else:
        st.session_state['new_person_data'] = None

def add_to_existing_household_interface():
    """Interface for adding people to existing households"""
    
    # Initialize session state for existing household workflow
    if 'existing_person' not in st.session_state:
        st.session_state['existing_person'] = None
    if 'existing_household' not in st.session_state:
        st.session_state['existing_household'] = None
    if 'household_members' not in st.session_state:
        st.session_state['household_members'] = []
    if 'new_person_data' not in st.session_state:
        st.session_state['new_person_data'] = None
    
    st.markdown("### 🔍 Find Existing Person/Household")
    
    # Search method selection
    search_method = st.radio(
        "How would you like to find the existing person?",
        ["By Name", "By Account Number"],
        key="existing_search_method"
    )
    
    # Search for existing person
    col1, col2 = st.columns(2)
    
    if search_method == "By Name":
        with col1:
            existing_first = st.text_input(
                "Existing Person - First Name", 
                key="existing_first",
                on_change=auto_search_existing_person_by_name,
                placeholder="Start typing to search automatically..."
            )
            existing_last = st.text_input(
                "Existing Person - Last Name", 
                key="existing_last",
                on_change=auto_search_existing_person_by_name,
                placeholder="Start typing to search automatically..."
            )
    
    else:  # By Account Number
        with col1:
            existing_account = st.text_input(
                "Existing Person - Account Number", 
                key="existing_account",
                on_change=auto_search_existing_person_by_account,
                placeholder="Type account number to search automatically..."
            )
    
    # Display results from session state
    if search_method == "By Name":
        existing_first = st.session_state.get('existing_first', '').strip()
        existing_last = st.session_state.get('existing_last', '').strip()
        if existing_first and existing_last and not st.session_state.get('existing_person'):
            st.error("❌ Person not found - try different spelling or use Account Number")
    else:
        existing_account = st.session_state.get('existing_account', '').strip()
        if existing_account and not st.session_state.get('existing_person'):
            st.error("❌ Account number not found")
            
    if st.session_state['existing_person']:
        existing_person = st.session_state['existing_person']
        existing_household = st.session_state['existing_household']
        household_members = st.session_state['household_members']
        
        st.success(f"✅ Found: {existing_person['FirstName']} {existing_person['LastName']} (ID: {existing_person['Id']})")
        
        if existing_household:
            st.success(f"🏠 Found household: {existing_household['FullName']} (ID: {existing_household['Id']})")
        else:
            st.warning("⚠️ This person is not currently in a household")
    
        # Show household members if household exists
        if existing_household:
            st.markdown("---")
            st.markdown("### 👥 Current Household Members")
            
            if household_members:
                for member in household_members:
                    role = member.get("_household_role", "Member")
                    st.text(f"• {member['FirstName']} {member['LastName']} ({role}) - ID: {member['Id']}")
            
            # Determine what type of addition we're doing
            st.markdown("---")
            st.markdown("### ➕ Add New Person")
            
            addition_type = st.radio(
                "What type of person are you adding?",
                ["Child to Parents", "Spouse to Single Person", "Other Family Member"],
                key="addition_type"
            )
            
            # Interface for adding new person
            new_person_search_method = st.radio(
                "How would you like to identify the new person?",
                ["By Name", "By Account Number"],
                key="new_person_search_method"
            )
            
            if new_person_search_method == "By Name":
                col3, col4 = st.columns(2)
                
                with col3:
                    new_first = st.text_input(
                        "New Person - First Name", 
                        key="new_first",
                        on_change=auto_search_new_person_by_name,
                        placeholder="Start typing to search automatically..."
                    )
                    new_last = st.text_input(
                        "New Person - Last Name", 
                        key="new_last", 
                        on_change=auto_search_new_person_by_name,
                        placeholder="Start typing to search automatically..."
                    )
            
            else:  # By Account Number
                col3, col4 = st.columns(2)
                
                with col3:
                    new_account = st.text_input(
                        "New Person - Account Number", 
                        key="new_account",
                        on_change=auto_search_new_person_by_account,
                        placeholder="Type account number to search automatically..."
                    )
            
            # Display new person search status and results
            if new_person_search_method == "By Name":
                new_first = st.session_state.get('new_first', '').strip()
                new_last = st.session_state.get('new_last', '').strip()
                if new_first and new_last and not st.session_state.get('new_person_data'):
                    st.error("❌ Person not found - they will be created as new")
                elif not new_first or not new_last:
                    if new_first or new_last:  # Only show if partially filled
                        st.info("ℹ️ Enter both first and last name to search")
            else:
                new_account = st.session_state.get('new_account', '').strip()
                if new_account and not st.session_state.get('new_person_data'):
                    st.error("❌ Account number not found - they will be created as new")
            
            # Display new person results from session state
            if st.session_state['new_person_data']:
                new_person = st.session_state['new_person_data']
                if new_person_search_method == "By Account Number":
                    new_first = new_person['FirstName']
                    new_last = new_person['LastName']
                
                st.success(f"✅ Found: {new_person['FirstName']} {new_person['LastName']} (ID: {new_person.get('Id', 'New')})")
                
                # Check if they're already in a household
                if new_person.get('Id'):
                    new_person_household = check_existing_household(new_person)
                    if new_person_household:
                        st.warning(f"⚠️ This person is already in household: {new_person_household['FullName']}")
            
            # Select relationship for the new person
            if addition_type == "Child to Parents":
                new_relationship = st.selectbox(
                    "New person will be:",
                    ["daughter", "son"],
                    key="new_person_relationship",
                    help="Select what relationship the new person will have to the household"
                )
            elif addition_type == "Spouse to Single Person":
                new_relationship = st.selectbox(
                    "New person will be:",
                    ["husband", "wife"],
                    key="new_person_relationship_spouse",
                    help="Select what relationship the new person will have to the existing person"
                )
            else:  # Other Family Member
                new_relationship = st.selectbox(
                    "New person will be:",
                    ["daughter", "son", "mother", "father", "sister", "brother", "husband", "wife"],
                    key="new_person_relationship_other",
                    help="Select what relationship the new person will have to the household"
                )
            
            # Preview and execute addition
            if st.session_state['new_person_data'] and st.session_state['existing_person']:
                new_person = st.session_state['new_person_data']
                existing_person = st.session_state['existing_person']
                
                st.markdown("---")
                st.markdown("### 👀 Preview Addition")
                
                # Show what will happen
                if addition_type == "Child to Parents":
                    st.text(f"Adding: {new_person['FirstName']} {new_person['LastName']} ({new_relationship})")
                    st.text(f"To household: {existing_household['FullName']}")
                    
                    # Initialize session state for member roles
                    if 'member_roles' not in st.session_state:
                        st.session_state['member_roles'] = {}
                    
                    st.markdown("**Select relationships for each person:**")
                    
                    # Let user select role for each household member
                    for member in household_members:
                        member_id = member['Id']
                        
                        # Check if they already have a parent role from existing relationships
                        existing_role = get_parent_role_from_existing_relationships(member_id)
                        
                        if existing_role:
                            st.session_state['member_roles'][member_id] = existing_role
                            st.text(f"• {member['FirstName']} - automatically detected as {existing_role} (from existing relationships)")
                        else:
                            # Determine what options this person should have
                            relationships = get_existing_relationships(member['Id'])
                            
                            is_parent = False
                            is_sibling = False
                            
                            for rel in relationships:
                                if not isinstance(rel, dict):
                                    continue
                                    
                                # Check what role this member has in relationships
                                if rel.get('AccountId1') == member['Id']:
                                    role = rel.get('Role1', '').lower()
                                elif rel.get('AccountId2') == member['Id']:
                                    role = rel.get('Role2', '').lower()
                                else:
                                    continue
                                
                                if role in ['mother', 'father']:
                                    is_parent = True
                                elif role in ['brother', 'sister', 'son', 'daughter']:
                                    is_sibling = True
                            
                            # Determine dropdown options based on existing relationships
                            if is_parent:
                                options = ["father", "mother"]
                                default_idx = 0
                            elif is_sibling:
                                options = ["brother", "sister"]
                                default_idx = 0
                            else:
                                options = ["father", "mother", "brother", "sister"]
                                default_idx = 0
                            
                            # Get current value or default
                            current_value = st.session_state['member_roles'].get(member_id, options[default_idx])
                            
                            # Selectbox for role selection
                            selected_role = st.selectbox(
                                f"{member['FirstName']} will be:",
                                options,
                                index=options.index(current_value) if current_value in options else default_idx,
                                key=f"member_role_{member_id}",
                                help=f"Select {member['FirstName']}'s relationship to {new_person['FirstName']}"
                            )
                            
                            # Update the member roles
                            st.session_state['member_roles'][member_id] = selected_role
                    
                    # Calculate individual relationship pairs
                    st.markdown("**Relationships to create:**")
                    relationship_pairs = {}
                    
                    for member in household_members:
                        member_id = member['Id']
                        member_role = st.session_state['member_roles'].get(member_id, 'father')
                        
                        # Get the relationship pair using the new logic
                        member_to_new, new_to_member = get_relationship_pair(member_role, new_relationship)
                        relationship_pairs[member_id] = (member_to_new, new_to_member)
                        
                        # Display the relationship
                        st.text(f"• {member['FirstName']} ({member_to_new}) ↔ {new_person['FirstName']} ({new_to_member})")


                elif addition_type == "Spouse to Single Person":
                    st.text(f"Adding: {new_person['FirstName']} {new_person['LastName']} ({new_relationship})")
                    st.text(f"To: {existing_person['FirstName']} {existing_person['LastName']}")
                    
                    # Show new household names
                    existing_rel = "wife" if new_relationship == "husband" else "husband"
                    new_household_names = format_household_names_with_relationship(
                        existing_person['FirstName'], existing_person['LastName'],
                        new_person['FirstName'], new_person['LastName'],
                        existing_rel, new_relationship
                    )
                    
                    st.text("New household names:")
                    for key, value in new_household_names.items():
                        st.text(f"• {key}: {value}")
                    
                    st.text("Relationship to create:")
                    st.text(f"• {existing_person['FirstName']} ({existing_rel}) ↔ {new_person['FirstName']} ({new_relationship})")
                
                # Execute button
                if st.button("🚀 Add to Household", type="primary", key="execute_addition"):
                    with st.spinner("Adding person to household..."):
                        success = False
                        
                        if addition_type == "Child to Parents":
                            # Add child to household
                            success = add_member_to_household(existing_household['Id'], new_person)
                            
                            if success:
                                st.success("✅ Child added to household!")
                                
                                # Create individual relationships using the relationship pairs
                                relationship_pairs = {}
                                member_roles = st.session_state.get('member_roles', {})
                                
                                # Recalculate relationship pairs for execution
                                for member in household_members:
                                    member_id = member['Id']
                                    member_role = member_roles.get(member_id, 'father')
                                    member_to_new, new_to_member = get_relationship_pair(member_role, new_relationship)
                                    relationship_pairs[member_id] = (member_to_new, new_to_member)
                                
                                # Create each individual relationship
                                for member in household_members:
                                    member_id = member['Id']
                                    member_to_new, new_to_member = relationship_pairs[member_id]
                                    
                                    if create_relationship(member_id, new_person['Id'], member_to_new, new_to_member):
                                        st.success(f"✅ Created relationship: {member['FirstName']} ({member_to_new}) ↔ {new_person['FirstName']} ({new_to_member})")
                                    else:
                                        st.warning(f"⚠️ Could not create relationship: {member['FirstName']} ({member_to_new}) ↔ {new_person['FirstName']} ({new_to_member})")

                        elif addition_type == "Spouse to Single Person":
                            # Add spouse to household and update names
                            success = add_member_to_household(existing_household['Id'], new_person)
                            
                            if success:
                                # Update household names
                                existing_rel = "wife" if new_relationship == "husband" else "husband"
                                new_household_names = format_household_names_with_relationship(
                                    existing_person['FirstName'], existing_person['LastName'],
                                    new_person['FirstName'], new_person['LastName'],
                                    existing_rel, new_relationship
                                )
                                
                                if update_household_names(existing_household['Id'], new_household_names):
                                    st.success("✅ Spouse added and household names updated!")
                                    
                                    # Create spouse relationship
                                    if create_relationship(existing_person['Id'], new_person.get('Id', 0), existing_rel, new_relationship):
                                        st.success(f"✅ Created relationship: {existing_person['FirstName']} ({existing_rel}) ↔ {new_person['FirstName']} ({new_relationship})")
                        
                        if success:
                            # Clear the session state to start fresh
                            st.session_state['existing_person'] = None
                            st.session_state['existing_household'] = None
                            st.session_state['household_members'] = []
                            st.session_state['new_person_data'] = None
                            st.success("🎉 Process completed! You can start a new addition.")
                            
                            if st.button("🔄 Start New Addition", key="start_new"):
                                st.rerun()
                        else:
                            st.error("❌ Failed to add person to household")

def get_relationship_pair(member_role, new_person_base_relationship):
    """
    Determine the bidirectional relationship between a household member and new person.
    
    Args:
        member_role: The role of the existing household member (father, mother, brother, sister)
        new_person_base_relationship: Base relationship of new person (daughter, son, etc.)
    
    Returns:
        Tuple of (member_role_to_new_person, new_person_role_to_member)
    """
    member_role = member_role.lower()
    base_rel = new_person_base_relationship.lower()
    
    # Parent-Child relationships
    if member_role in ['father', 'mother']:
        if base_rel in ['daughter', 'son']:
            # Parent to child
            return (member_role, base_rel)
        elif base_rel in ['brother', 'sister']:
            # If new person is marked as sibling but member is parent, 
            # convert to parent-child relationship
            child_rel = 'daughter' if base_rel == 'sister' else 'son'
            return (member_role, child_rel)
        else:
            # Default parent-child
            return (member_role, 'daughter' if member_role == 'mother' else 'son')
    
    # Sibling relationships
    elif member_role in ['brother', 'sister']:
        if base_rel in ['daughter', 'son']:
            # If new person is marked as child but member is sibling,
            # convert to sibling relationship
            # FIXED: Use base_rel (new person's relationship) to determine the sibling type
            opposite_sibling = 'sister' if base_rel == 'daughter' else 'brother'
            return (member_role, opposite_sibling)
        elif base_rel in ['brother', 'sister']:
            # Both are siblings
            return (member_role, base_rel)
        else:
            # Default sibling relationship
            opposite_sibling = 'sister' if member_role == 'brother' else 'brother'
            return (member_role, opposite_sibling)
    
    # Child to parent relationships (if member is marked as child)
    elif member_role in ['daughter', 'son']:
        if base_rel in ['father', 'mother']:
            # New person is parent to existing child
            return (member_role, base_rel)
        elif base_rel in ['daughter', 'son']:
            # Both are children - make them siblings
            member_sibling = 'sister' if member_role == 'daughter' else 'brother'
            new_sibling = 'sister' if base_rel == 'daughter' else 'brother'
            return (member_sibling, new_sibling)
        elif base_rel in ['brother', 'sister']:
            # Member is child, new person is sibling
            member_sibling = 'sister' if member_role == 'daughter' else 'brother'
            return (member_sibling, base_rel)
        else:
            # Default sibling relationship
            member_sibling = 'sister' if member_role == 'daughter' else 'brother'
            new_sibling = 'sister' if member_sibling == 'brother' else 'brother'
            return (member_sibling, new_sibling)
    
    # Fallback - treat as generic family relationship
    else:
        return (member_role, base_rel)
    
def add_member_to_household(household_id: int, new_member_data: Dict) -> bool:
    """Add an existing member to a household using constituent update (WORKING METHOD)"""
    try:
        # Get the new member ID
        new_member_id = new_member_data.get('Id')
        if not new_member_id:
            st.error("New member data missing ID")
            return False
        
        # Method 3: Update the constituent's HouseholdId directly (THIS WORKS!)
        update_payload = {
            "Id": new_member_id,
            "Type": "Individual",
            "Status": "Active",
            "FirstName": new_member_data.get("FirstName"),
            "LastName": new_member_data.get("LastName"),
            "HouseholdId": household_id
        }
        
        # Update constituent with household ID
        url = f"{API_BASE_URL}/constituent/{new_member_id}"
        response = requests.put(url, headers=HEADERS, json=update_payload)
        
        if response.status_code in [200, 201]:
            if household_id in st.session_state.get('cached_households', {}):
                del st.session_state['cached_households'][str(household_id)]
            if household_id in st.session_state.get('cached_household_members', {}):
                del st.session_state['cached_household_members'][str(household_id)]
            updated_constituent = get_constituent_by_id(new_member_id)
            if updated_constituent and updated_constituent.get("HouseholdId") == household_id:
                st.success(f"✅ Successfully added {new_member_data.get('FirstName')} to household!")
                return True
            else:
                st.error("❌ API returned success but household wasn't updated")
                return False
        else:
            st.error(f"API Error {response.status_code}: {response.text}")
            return False
        
    except Exception as e:
        st.error(f"Error adding member to household: {str(e)}")
        return False

def main():
    if 'cached_constituents' not in st.session_state:
        st.session_state['cached_constituents'] = {}
    if 'cached_households' not in st.session_state:
        st.session_state['cached_households'] = {}
    if 'cached_household_members' not in st.session_state:
        st.session_state['cached_household_members'] = {}    

    st.title("🏠 Bloomerang Household Manager")
    st.markdown("Create new households or add people to existing households")
    
    with st.expander("📖 Family Types & Instructions"):
        st.markdown("""
        ### Family Types
        **Married Parents + Children:**
        - Person 1: husband, Person 2: wife
        - Children: daughter/son to both parents
        - Naming: "The [Husband's Name] Family"
        
        **Unmarried Parents + Children:**
        - Person 1: father, Person 2: mother
        - Children: daughter/son to both parents
        - Naming: Different last name format
        
        **Siblings are automatically related:**
        - daughter + daughter = sisters
        - son + son = brothers
        - daughter + son = sister + brother
        
        ### Adding to Existing Households
        - **Child to Parents**: Finds existing household, adds child, creates all parent relationships
        - **Spouse to Single Person**: Adds spouse and updates household names automatically
        - **Other Family**: Creates custom relationships as specified
        """)
    
    # Tab selection
    tab1, tab2 = st.tabs(["🆕 Create New Household", "➕ Add to Existing Household"])
    
    with tab1:
        st.markdown("### Create a New Household")
        create_new_household_interface()
    
    with tab2:
        st.markdown("### Add People to Existing Household")
        add_to_existing_household_interface()    

if __name__ == "__main__":
    main()