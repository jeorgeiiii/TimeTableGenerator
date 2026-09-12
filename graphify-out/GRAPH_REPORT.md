# Graph Report - TimeTableGenerator  (2026-09-02)

## Corpus Check
- 155 files · ~65,928 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1294 nodes · 1815 edges · 176 communities (66 shown, 83 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 34 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Legacy Backend API (Monolith)
- Toast Notification Hook
- Sidebar UI Component
- Carousel UI Component
- Admin Routes
- Course & Scheduler Factory (Root Copy)
- Environment Test Script
- Backend Auth (Root Copy)
- Simple Scheduler Script
- Auth Middleware
- DB Query Helpers
- TS App Config
- Pydantic Data Models
- Timetable API (Root Script)
- Timetable Routes
- React App Shell
- Assign Subject Page
- C-Program Scheduler Wrapper
- FastAPI App Entrypoint
- Course Class & Rationale (Legacy)
- Command Palette UI
- TS Node Config
- Course Routes
- Scheduling Rationale Notes (Legacy)
- shadcn/ui Components Config
- Frontend Query Service
- Admin Settings Page
- Form UI Component
- Timetable Service (DB-backed)
- Package
- Bipartite Matching Core (Legacy)
- Room & Student Group Classes (Legacy)
- Room Routes
- Package
- Slot Routes
- Menubar UI Component
- Project README
- Chart UI Component
- Frontend Timetable Service
- Tsconfig
- SQLite Database Layer
- Auth Context UI Component
- Context Menu UI Component
- Dropdown Menu UI Component
- Frontend Auth Service
- Package
- App Sidebar UI Component
- Breadcrumb UI Component
- Drawer UI Component
- Navigation Menu UI Component
- Teacher Schedule UI Component
- Timetable Service
- Config Module
- Faculty Routes
- Auth Service
- Timetable UI Component
- Timetable UI Component
- Toggle Group UI Component
- Teacher Scheduling (Legacy)
- App Main Entrypoint
- Timetable Service
- Package
- Alert UI Component
- Input Otp UI Component
- Accordion UI Component
- Avatar UI Component
- Badge UI Component
- Tabs UI Component
- Add Users
- Auth
- Models
- Requirements
- Nav Link UI Component
- Radio Group UI Component
- Textarea UI Component
- Test Connection UI Component
- Package
- Package
- Package
- Package
- Placeholder Logo (SVG)
- Sample Course Data File
- Package
- Package
- Package
- Package
- .gitignore Rules
- Vite HTML Entrypoint
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Package
- Checkbox UI Component
- Hover Card UI Component
- Progress UI Component
- Slider UI Component
- Switch UI Component
- Vercel Deployment Config
- robots.txt Crawler Policy

## God Nodes (most connected - your core abstractions)
1. `get_db()` - 36 edges
2. `TimetableScheduler` - 23 edges
3. `decode_token()` - 21 edges
4. `compilerOptions` - 19 edges
5. `get_db()` - 18 edges
6. `ApiResponse` - 17 edges
7. `TimetableScheduler` - 16 edges
8. `DBQueries` - 16 edges
9. `compilerOptions` - 14 edges
10. `TimetableScheduler` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Backend Tech Stack (FastAPI+SQLite+JWT)` --semantically_similar_to--> `mysql-connector-python Dependency`  [AMBIGUOUS] [semantically similar]
  Readme.md → backend/requirements.txt
- `Dashboard's Expected Endpoint Contract (branch/year/section paths)` --semantically_similar_to--> `Documented API Endpoints`  [AMBIGUOUS] [semantically similar]
  templates/dashboard.html → Readme.md
- `Backend Core Dependency Set (FastAPI/pydantic/pandas)` --semantically_similar_to--> `Root Requirements (fastapi/uvicorn/pyjwt)`  [INFERRED] [semantically similar]
  backend/requirements.txt → requirements.txt
- `login()` --calls--> `get_db()`  [INFERRED]
  backend/main.py → backend/database.py
- `signup()` --calls--> `get_db()`  [INFERRED]
  backend/main.py → backend/database.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Lovable-Scaffolded Frontend Boilerplate** — frontend_readme_lovable_stub, frontend_index_lovable_branding, frontend_gitignore_build_artifacts [INFERRED 0.75]

## Communities (176 total, 83 thin omitted)

### Community 0 - "Legacy Backend API (Monolith)"
Cohesion: 0.08
Nodes (65): add_course(), add_course_assignment(), add_holiday(), add_room(), add_subject(), add_teacher(), assign_subject(), _build_timetable_response() (+57 more)

### Community 1 - "Toast Notification Hook"
Cohesion: 0.06
Nodes (46): TimetableGenerator(), Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, SelectContent (+38 more)

### Community 2 - "Sidebar UI Component"
Cohesion: 0.06
Nodes (37): Input, Separator, SheetContent, SheetContentProps, SheetDescription, SheetOverlay, SheetTitle, sheetVariants (+29 more)

### Community 3 - "Carousel UI Component"
Cohesion: 0.07
Nodes (28): AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogOverlay, AlertDialogTitle, Button, ButtonProps (+20 more)

### Community 4 - "Admin Routes"
Cohesion: 0.08
Nodes (37): require_admin(), add_subject(), add_teacher(), assign_subject(), create_section(), delete_subject(), delete_teacher(), delete_user() (+29 more)

### Community 5 - "Course & Scheduler Factory (Root Copy)"
Cohesion: 0.07
Nodes (14): Course, create_timetable_scheduler(), Teacher with availability and schedule tracking, Enhanced scheduler with collision prevention, Generate timetable using priority-based assignment, Create a fully configured timetable scheduler, Student group/section with schedule tracking, Room/classroom with capacity and schedule (+6 more)

### Community 6 - "Environment Test Script"
Cohesion: 0.09
Nodes (28): generate_timetable(), hash_password(), Create test database with all tables, Simple timetable scheduler with collision prevention, Check if teacher is free at given time, Check if room is free at given time, Check if student group is free at given time, Assign a class to a time slot (+20 more)

### Community 7 - "Backend Auth (Root Copy)"
Cohesion: 0.10
Nodes (30): add_subject(), add_teacher(), assign_subject_to_teacher(), create_section(), generate_timetable(), get_all_subjects(), get_all_teachers(), get_branches() (+22 more)

### Community 8 - "Simple Scheduler Script"
Cohesion: 0.11
Nodes (7): Course, create_scheduler(), Room, StudentGroup, Teacher, TimeSlot, TimetableScheduler

### Community 9 - "Auth Middleware"
Cohesion: 0.12
Nodes (23): authenticate_user(), create_access_token(), get_password_hash(), create_token(), Verify password against hash, Authenticate user from database, Create JWT access token, Create JWT token for user (+15 more)

### Community 10 - "DB Query Helpers"
Cohesion: 0.12
Nodes (11): get_db(), init_db(), insert_sample_data(), Get database connection with context manager, Initialize all database tables with complete schema, Insert comprehensive sample data for testing, DBQueries, Get time slots where teacher is available (+3 more)

### Community 11 - "TS App Config"
Cohesion: 0.08
Nodes (25): compilerOptions, allowImportingTsExtensions, isolatedModules, jsx, lib, module, moduleDetection, moduleResolution (+17 more)

### Community 12 - "Pydantic Data Models"
Cohesion: 0.16
Nodes (24): AdminStatsResponse, ChangePasswordRequest, Config, CourseBase, CourseResponse, FacultyBase, FacultyCreate, FacultyResponse (+16 more)

### Community 13 - "Timetable API (Root Script)"
Cohesion: 0.16
Nodes (20): add_subject(), add_teacher(), assign_subject_to_teacher(), create_section(), generate_timetable(), get_branches(), get_dashboard(), get_subjects() (+12 more)

### Community 14 - "Timetable Routes"
Cohesion: 0.14
Nodes (19): ConflictResolution, generate_timetable(), GenerateRequest, get_conflicts(), get_group_schedule(), get_teacher_schedule(), get_timetable(), get_timetable_stats() (+11 more)

### Community 15 - "React App Shell"
Cohesion: 0.14
Nodes (11): App(), queryClient, SpaceScene(), Toaster(), ToasterProps, Index(), LoginPage(), roleConfig (+3 more)

### Community 16 - "Assign Subject Page"
Cohesion: 0.15
Nodes (12): AddSubject(), Teacher, AddTeacher(), Teacher, AssignSubject(), SubjectResponse, TeacherResponse, yearLabelToInt() (+4 more)

### Community 17 - "C-Program Scheduler Wrapper"
Cohesion: 0.16
Nodes (10): Any, Map semester to color codes (from new.c's color array), Parse all generated timetable files, Parse timetable text content (tab-separated format from new.c), Generate timetable using your C program (new.c / tt.exe), Run the C executable (compiled from new.c), Run Python scheduler as fallback, Wrapper for your existing C scheduling algorithm (+2 more)

### Community 18 - "FastAPI App Entrypoint"
Cohesion: 0.26
Nodes (17): generate_timetable(), get_course_assignments(), get_courses(), get_db(), get_groups(), get_rooms(), get_stats(), get_teachers() (+9 more)

### Community 19 - "Course Class & Rationale (Legacy)"
Cohesion: 0.12
Nodes (9): Course, Course with teacher and group assignments, Check if teacher is already assigned to this slot, Check if student group already has a class at this slot, Check if room is already booked at this slot, Check all possible conflicts for a course assignment, Assign a course to a specific slot and room with conflict checking, Generate timetable using priority-based assignment (+1 more)

### Community 20 - "Command Palette UI"
Cohesion: 0.12
Nodes (12): Command, CommandDialogProps, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator (+4 more)

### Community 21 - "TS Node Config"
Cohesion: 0.11
Nodes (17): compilerOptions, allowImportingTsExtensions, isolatedModules, lib, module, moduleDetection, moduleResolution, noEmit (+9 more)

### Community 22 - "Course Routes"
Cohesion: 0.21
Nodes (16): decode_token(), CourseCreate, CourseUpdate, create_course(), delete_course(), get_all_courses(), get_course(), delete (+8 more)

### Community 23 - "Scheduling Rationale Notes (Legacy)"
Cohesion: 0.17
Nodes (9): Enhanced scheduler with collision prevention and bipartite matching, Get formatted schedule for a teacher, Get formatted schedule for a student group, Get formatted schedule for a room, Get all schedules in one object, Export entire scheduler state to dictionary, Export entire scheduler state to JSON string, Export timetable to formatted text file (+1 more)

### Community 24 - "shadcn/ui Components Config"
Cohesion: 0.12
Nodes (16): aliases, components, hooks, lib, ui, utils, rsc, $schema (+8 more)

### Community 25 - "Frontend Query Service"
Cohesion: 0.22
Nodes (14): AdminDashboard(), CreateSection(), fetchSubjects(), fetchTeachers(), fetchTimetable(), fetchUsers(), queryKeys, useAddSubject() (+6 more)

### Community 26 - "Admin Settings Page"
Cohesion: 0.15
Nodes (9): AdminSidebar(), helpLinks, mainLinks, managementLinks, accountSettings, preferences, security, mockUsers (+1 more)

### Community 27 - "Form UI Component"
Cohesion: 0.19
Nodes (12): FormControl, FormDescription, FormFieldContext, FormFieldContextValue, FormItem, FormItemContext, FormItemContextValue, FormLabel (+4 more)

### Community 28 - "Timetable Service (DB-backed)"
Cohesion: 0.21
Nodes (7): get_db(), Get database connection with context manager, create_sample_timetable(), create_timetable_scheduler(), Create a fully configured timetable scheduler for FastAPI, Create and generate a sample timetable (for testing), TimetableService

### Community 29 - "Package"
Cohesion: 0.15
Nodes (13): autoprefixer, eslint, devDependencies, autoprefixer, eslint, globals, @playwright/test, @tailwindcss/typography (+5 more)

### Community 30 - "Bipartite Matching Core (Legacy)"
Cohesion: 0.23
Nodes (8): AssignmentProblem(), BipartiteGraph, MaximumCardinalityMatching(), TimeSlot, generate_timetable_from_files(), Main function to generate timetable from existing data files, TestAssignmentProblem(), TestMaximumBipartiteMatching()

### Community 31 - "Room & Student Group Classes (Legacy)"
Cohesion: 0.17
Nodes (4): Student group/section with schedule tracking, Room/classroom with capacity and schedule, Room, StudentGroup

### Community 32 - "Room Routes"
Cohesion: 0.21
Nodes (12): RoomBase, RoomCreate, RoomResponse, create_room(), delete_room(), get_all_rooms(), delete, get (+4 more)

### Community 33 - "Package"
Cohesion: 0.15
Nodes (13): date-fns, dependencies, date-fns, input-otp, @radix-ui/react-avatar, @radix-ui/react-progress, react-dom, tailwindcss-animate (+5 more)

### Community 34 - "Slot Routes"
Cohesion: 0.23
Nodes (11): ApiResponse, create_slot(), delete_slot(), get_all_slots(), delete, get, HTTPAuthorizationCredentials, post (+3 more)

### Community 35 - "Menubar UI Component"
Cohesion: 0.17
Nodes (10): Menubar, MenubarCheckboxItem, MenubarContent, MenubarItem, MenubarLabel, MenubarRadioItem, MenubarSeparator, MenubarSubContent (+2 more)

### Community 36 - "Project README"
Cohesion: 0.18
Nodes (11): mysql-connector-python Dependency, Documented API Endpoints, Separate Backend Deployment (Railway/Render/Heroku), Backend Tech Stack (FastAPI+SQLite+JWT), Frontend Tech Stack (React+TS+Vite+Tailwind), Multi-role Authentication (Admin/Teacher/Student), SGSITS Timetable Generator (Project), Vercel Frontend Deployment (+3 more)

### Community 37 - "Chart UI Component"
Cohesion: 0.25
Nodes (9): ChartConfig, ChartContainer, ChartContext, ChartContextProps, ChartLegendContent, ChartTooltipContent, getPayloadConfigFromPayload(), THEMES (+1 more)

### Community 38 - "Frontend Timetable Service"
Cohesion: 0.25
Nodes (9): hasTimetableData(), StudentDashboard(), yearStringToNumber(), yearToSemester(), ApiResponse, Branch, Subject, Teacher (+1 more)

### Community 39 - "Tsconfig"
Cohesion: 0.18
Nodes (10): compilerOptions, allowJs, noImplicitAny, noUnusedLocals, noUnusedParameters, paths, skipLibCheck, strictNullChecks (+2 more)

### Community 40 - "SQLite Database Layer"
Cohesion: 0.27
Nodes (5): Database, Get database connection, Execute SELECT query and return results, Execute INSERT query and return last inserted ID, Execute UPDATE/DELETE query and return success status

### Community 41 - "Auth Context UI Component"
Cohesion: 0.24
Nodes (7): ProtectedRoute(), ProtectedRouteProps, AuthContext, AuthContextType, SignupData, useAuth(), User

### Community 42 - "Context Menu UI Component"
Cohesion: 0.20
Nodes (8): ContextMenuCheckboxItem, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuRadioItem, ContextMenuSeparator, ContextMenuSubContent, ContextMenuSubTrigger

### Community 43 - "Dropdown Menu UI Component"
Cohesion: 0.20
Nodes (8): DropdownMenuCheckboxItem, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuRadioItem, DropdownMenuSeparator, DropdownMenuSubContent, DropdownMenuSubTrigger

### Community 45 - "Package"
Cohesion: 0.22
Nodes (9): scripts, build, build:dev, dev, lint, preview, test, test:watch (+1 more)

### Community 46 - "App Sidebar UI Component"
Cohesion: 0.32
Nodes (4): AppSidebar(), menuItems, Props, StarBackground()

### Community 47 - "Breadcrumb UI Component"
Cohesion: 0.25
Nodes (5): Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage

### Community 48 - "Drawer UI Component"
Cohesion: 0.25
Nodes (4): DrawerContent, DrawerDescription, DrawerOverlay, DrawerTitle

### Community 49 - "Navigation Menu UI Component"
Cohesion: 0.29
Nodes (7): NavigationMenu, NavigationMenuContent, NavigationMenuIndicator, NavigationMenuList, NavigationMenuTrigger, navigationMenuTriggerStyle, NavigationMenuViewport

### Community 50 - "Teacher Schedule UI Component"
Cohesion: 0.32
Nodes (5): TeacherDashboard(), DAYS, ScheduleEntry, TeacherSchedule(), ViewTimetable()

### Community 53 - "Faculty Routes"
Cohesion: 0.29
Nodes (7): create_faculty(), get_all_faculty(), get, HTTPAuthorizationCredentials, post, Get all faculty members, Create a new faculty member (Admin only)

### Community 54 - "Auth Service"
Cohesion: 0.29
Nodes (4): GoogleLoginButtonProps, AuthResponse, SignupData, User

### Community 55 - "Timetable UI Component"
Cohesion: 0.33
Nodes (6): COLORS, DAYS, getColorForSubject(), TIME_SLOTS, Timetable(), TimetableEntry

### Community 56 - "Timetable UI Component"
Cohesion: 0.33
Nodes (6): COLORS, DAYS, getColorForSubject(), TIME_SLOTS, Timetable(), TimetableEntry

### Community 57 - "Toggle Group UI Component"
Cohesion: 0.43
Nodes (5): ToggleGroup, ToggleGroupContext, ToggleGroupItem, Toggle, toggleVariants

### Community 59 - "App Main Entrypoint"
Cohesion: 0.60
Nodes (5): hash_password(), login(), post, signup(), verify_password()

### Community 60 - "Timetable Service"
Cohesion: 0.33
Nodes (5): Course, Room, Slot, TimetableResponse, timetableService

### Community 61 - "Package"
Cohesion: 0.40
Nodes (4): name, private, type, version

### Community 62 - "Alert UI Component"
Cohesion: 0.50
Nodes (4): Alert, AlertDescription, AlertTitle, alertVariants

### Community 63 - "Input Otp UI Component"
Cohesion: 0.40
Nodes (4): InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot

### Community 64 - "Accordion UI Component"
Cohesion: 0.50
Nodes (3): AccordionContent, AccordionItem, AccordionTrigger

### Community 65 - "Avatar UI Component"
Cohesion: 0.50
Nodes (3): Avatar, AvatarFallback, AvatarImage

### Community 66 - "Badge UI Component"
Cohesion: 0.67
Nodes (3): Badge(), BadgeProps, badgeVariants

### Community 67 - "Tabs UI Component"
Cohesion: 0.50
Nodes (3): TabsContent, TabsList, TabsTrigger

### Community 69 - "Auth"
Cohesion: 0.67
Nodes (3): get_current_user(), HTTPAuthorizationCredentials, Get current user from JWT token

### Community 71 - "Requirements"
Cohesion: 0.67
Nodes (3): Backend Core Dependency Set (FastAPI/pydantic/pandas), Quickstart pip install Command, Root Requirements (fastapi/uvicorn/pyjwt)

## Ambiguous Edges - Review These
- `Backend Tech Stack (FastAPI+SQLite+JWT)` → `mysql-connector-python Dependency`  [AMBIGUOUS]
  backend/requirements.txt · relation: semantically_similar_to
- `Documented API Endpoints` → `Dashboard's Expected Endpoint Contract (branch/year/section paths)`  [AMBIGUOUS]
  templates/dashboard.html · relation: semantically_similar_to

## Knowledge Gaps
- **353 isolated node(s):** `Course`, `Room`, `Slot`, `TimetableResponse`, `timetableService` (+348 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 597 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **83 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Backend Tech Stack (FastAPI+SQLite+JWT)` and `mysql-connector-python Dependency`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **What is the exact relationship between `Documented API Endpoints` and `Dashboard's Expected Endpoint Contract (branch/year/section paths)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `TimetableScheduler` connect `C-Program Scheduler Wrapper` to `Config Module`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `TimetableScheduler` connect `Scheduling Rationale Notes (Legacy)` to `Course Class & Rationale (Legacy)`, `Teacher Scheduling (Legacy)`, `Timetable Service (DB-backed)`, `Bipartite Matching Core (Legacy)`, `Room & Student Group Classes (Legacy)`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `dependencies` connect `Package` to `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`, `Package`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **What connects `Course`, `Room`, `Slot` to the rest of the system?**
  _353 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Legacy Backend API (Monolith)` be split into smaller, more focused modules?**
  _Cohesion score 0.07507914970601538 - nodes in this community are weakly interconnected._