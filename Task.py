# creating the parent task

class Task:
    _id_counter = 0
    def __init__(self, title, due_date, flag, status = "Pending", description = None):
        Task._id_counter += 1
        self._task_id = Task._id_counter
        
        # other attributes
        self.title = title
        self.due_date = due_date
        self.status = status
        self._description = description
        self.flag = flag
    
    def get_task_id(self): 
        return self._task_id
    
    def set_description(self, description): 
        if len(description) > 15:
            raise "Description exceeds 15 characters. Please shorten your description!"
        self._description = description

    def get_description(self): 
        return self._description
    
    def mark_completed(self): 
        self.status = "Completed"
        return self.status
    
    def __str__(self):
        return f'Task_id:{self._task_id}  Title:{self.title}  Due Date:{self.due_date}  Status:{self.status}  Description:{self._description}  Type:{self.flag})'

# task = Task("Mr", "2024-11-22","Pending","Shopping","personal") 
# task2 = Task("Mr", "2024-11-22","personal","Pending",description="Shopping") 
# print(task2)
# print(task2.get_description())
# comp = task2.mark_completed()
# print(task2)

class PersonalTask(Task):
    def __init__(self, priority = "low"):
        self.priority = priority

    def is_high_priority(self):
        if self.priority.lower() == 'high':
            return True
        else:
            return False
    
    def set_priority(self, priority): 
        priority_list = ['high','medium','low']
        if priority.lower() in priority_list:
            try:
                self.priority = priority.lower()
            except:
                return ("You have provided an option that is not high, low or medium. Invalid entry.")
            

    def __str__(self):
        return super.__str__() + f'Priority: {" ".join(self.priority)}'
        
class WorkTask(Task):
    def __init__(self):
        self.team_members = [ ]

    def add_team_member(self, member):
        self.member = member
        self.team_members.append(self.member)
        return self.team_members
    
    def __str__(self):
         return super.__str__() + f'Team Members: {" ".join(self.team_members)}'
        