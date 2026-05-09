import math

def sigmoid(x: float) -> float:
    """Standard sigmoid function."""
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0

def calculate_attack_probability(p_reachable: float, days_since_login: float, pwd_age: float, has_pwd_last_set: bool = True) -> float:
    """
    Calculate the Bayesian updated probability of an attack:
    P = P_active * P_weak_pwd * P_reachable
    
    P_active = sigmoid((365 - days_since_login) / 100)
    P_weak_pwd = 1 if no pwdLastSet else sigmoid((180 - pwd_age) / 60)
    
    :param p_reachable: Base probability of reachable path (P_reachable).
    :param days_since_login: Days since the last login.
    :param pwd_age: Age of the password in days.
    :param has_pwd_last_set: True if the account has a pwdLastSet attribute, False otherwise.
    :return: Updated probability (0.0 to 1.0).
    """
    if not (0.0 <= p_reachable <= 1.0):
        raise ValueError("p_reachable must be between 0.0 and 1.0")

    # P_active
    p_active = sigmoid((365 - days_since_login) / 100)
    
    # P_weak_pwd
    if not has_pwd_last_set:
        p_weak_pwd = 1.0
    else:
        p_weak_pwd = sigmoid((180 - pwd_age) / 60)

    # Calculate final P
    p = p_active * p_weak_pwd * p_reachable
    
    return min(max(p, 0.0), 1.0)
